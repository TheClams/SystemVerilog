import sublime, sublime_plugin
import re, string, os, sys, functools, mmap

sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
import verilogutil
import sublimeutil

list_module_files = {}
lmf_update_ongoing = False

########################################
# Create module instantiation skeleton #
class VerilogModuleInstCommand(sublime_plugin.TextCommand):

    #TODO: Run the search in background and keep a cache to improve performance
    def run(self,edit):
        global list_module_files
        if len(self.view.sel())>0 :
            r = self.view.sel()[0]
            scope = self.view.scope_name(r.a)
            if 'meta.module.inst' in scope:
                self.view.run_command("verilog_module_reconnect")
                return
        self.window = sublime.active_window()
        # Populate the list_module_files:
        #  - if it exist use latest version and display panel immediately while running an update
        #  - if not display panel only when list is ready
        projname = self.window.project_file_name()
        if projname not in list_module_files:
            sublime.set_timeout_async(functools.partial(self.get_list_file,projname,functools.partial(self.on_list_done,projname)), 0)
            sublime.status_message('Please wait while module list is being built')
        elif not lmf_update_ongoing:
            sublime.set_timeout_async(functools.partial(self.get_list_file,projname), 0)
            self.on_list_done(projname)

    def get_list_file(self, projname, callback=None):
        global list_module_files
        global lmf_update_ongoing
        lmf_update_ongoing = True
        lmf = []
        for folder in sublime.active_window().folders():
            for root, dirs, files in os.walk(folder):
                for fn in files:
                    if fn.lower().endswith(('.v','.sv')):
                        ffn = os.path.join(root,fn)
                        f = open(ffn)
                        if os.stat(ffn).st_size:
                            s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                            if s.find(b'module') != -1:
                                lmf.append(ffn)
        sublime.status_message('List of module files updated')
        list_module_files[projname] = lmf[:]
        lmf_update_ongoing = False
        if callback:
            callback()

    def on_list_done(self,projname):
        self.window.show_quick_panel(list_module_files[projname], functools.partial(self.on_select_done,projname))

    def on_select_done(self, projname, index):
        # print ("Selected: " + str(index) + " " + list_module_files[projname][[index])
        if index >= 0:
            self.view.run_command("verilog_do_module_parse", {"args":{'fname':list_module_files[projname][index]}})

class VerilogDoModuleParseCommand(sublime_plugin.TextCommand):

    def run(self, edit, args):
        self.fname = args['fname']
        #TODO: check for multiple module in the file
        self.pm = verilogutil.parse_module_file(self.fname)
        # print(self.pm)
        if self.pm is not None:
            self.param_value = []
            if self.pm['param'] and self.view.settings().get('sv.fillparam'):
                self.cnt = 0
                self.show_prompt()
            else:
                self.view.run_command("verilog_do_module_inst", {"args":{'pm':self.pm, 'pv':self.param_value, 'text':self.fname}})

    def on_prompt_done(self, content):
        if not content.startswith("Default"):
            self.param_value.append({'name':self.pm['param'][self.cnt]['name'] , 'value': content});
        self.cnt += 1
        if self.pm['param'] is None:
            return
        if self.cnt < len(self.pm['param']):
            self.show_prompt()
        else:
            self.view.run_command("verilog_do_module_inst", {"args":{'pm':self.pm, 'pv':self.param_value, 'text':self.fname}})

    def show_prompt(self):
        p = self.pm['param'][self.cnt]
        panel = sublime.active_window().show_input_panel(p['name'], "Default: " + p['value'], self.on_prompt_done, None, None)
        #select the whole line (to ease value change)
        r = panel.line(panel.sel()[0])
        panel.sel().clear()
        panel.sel().add(r)


class VerilogDoModuleInstCommand(sublime_plugin.TextCommand):
    #TODO: check base indentation
    def run(self, edit, args):
        settings = self.view.settings()
        isAutoConnect = settings.get('sv.autoconnect')
        # pm = verilogutil.parse_module_file(args['text'])
        pm = args['pm']
        # print('[VerilogDoModuleInstCommand] pm = '+ str(pm))
        decl = ''
        ac = {}
        wc = {}
        # Add signal port declaration
        if isAutoConnect and pm['port']:
            (decl,ac,wc) = self.get_connect(self.view, settings, pm)
            #Find location where to insert signal declaration: default to just before module instantiation
            if decl != "":
                r = self.get_region_decl(self.view,settings)
                self.view.insert(edit, r, '\n'+decl)
                sublime.status_message('Adding ' + str(len(decl.splitlines())) + ' signals declaration' )

        # Instantiation
        inst = pm['name'] + " "
        # Parameters: bind only parameters for which a value different from default was set
        if len(args['pv']) > 0:
            max_len = max([len(x['name']) for x in args['pv']])
            inst += "#(\n"
            for i in range(len(args['pv'])):
                inst+= "\t." + args['pv'][i]['name'].ljust(max_len) + "("+args['pv'][i]['value']+")"
                if i<len(args['pv'])-1:
                    inst+=","
                inst+="\n"
            inst += ") "
        #Port binding
        inst += settings.get('sv.instance_prefix') + pm['name'] + settings.get('sv.instance_suffix') + " (\n"
        if pm['port']:
            # Get max length of a port to align everything
            max_len_p = max([len(x['name']) for x in pm['port']])
            max_len_s = max_len_p
            # print('Autoconnect dict = ' + str([ac[x] for x in ac]))
            if len(ac)>0 :
                max_len_s = max([len(ac[x]) for x in ac])
                if max_len_p>max_len_s:
                    max_len_s = max_len_p
            for i in range(len(pm['port'])):
                portname = pm['port'][i]['name']
                inst+= "\t." + portname.ljust(max_len_p) + "("
                if isAutoConnect:
                    if portname in ac.keys():
                        inst+= ac[portname].ljust(max_len_s)
                    else :
                        inst+= portname.ljust(max_len_s)
                inst+= ")"
                if i<len(pm['port'])-1:
                    inst+=","
                if portname in wc.keys():
                    inst+=" // TODO: Check connection ! " + wc[portname]
                inst+="\n"
        inst += ");\n"
        self.view.insert(edit, self.view.sel()[0].a, inst)
        # Status report
        nb_decl = len(decl.splitlines())
        s = ''
        if nb_decl:
            s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)\n'
        if len(ac)>0 :
            s+= 'Non-perfect name match for ' + str(len(ac)) + ' port(s) : ' + str(ac) + '\n'
        if len(wc)>0 :
            s+= 'Found ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()]) + '\n'
        if s!='':
            sublimeutil.print_to_panel(s,'sv')

    def get_region_decl(self, view, settings):
        r = view.sel()[0].begin()
        s = settings.get('sv.decl_start','')
        if s!='' :
            r_start = view.find(s,0,sublime.LITERAL)
            if r_start :
                s = settings.get('sv.decl_end','')
                r_stop = None
                if s!='':
                    r_stop = view.find(s,r_start.a,sublime.LITERAL)
                # Find first empty Find line
                if r_stop:
                    r_tmp = view.find_by_class(r_stop.a,False,sublime.CLASS_EMPTY_LINE)
                else :
                    r_tmp = view.find_by_class(r_start.a,True,sublime.CLASS_EMPTY_LINE)
                if r_tmp:
                    r = r_tmp
        return r

    def get_connect(self,view,settings,pm):
        # Init return variable
        decl = ""
        ac = {} # autoconnection (entry is port name)
        wc = {} # warning connection (entry is port name)
        # get settings
        indent_level = settings.get('sv.decl_indent')
        port_prefix = settings.get('sv.autoconnect_port_prefix')
        port_suffix = settings.get('sv.autoconnect_port_suffix')
        #default signal type to logic, except verilog file use wire (if type is implicit)
        fname = view.file_name()
        sig_type = 'logic'
        if fname.endswith('.v'):
            sig_type = 'wire'
        # read file to be able to check existing declaration
        flines = view.substr(sublime.Region(0, view.size()))
        mi = verilogutil.parse_module(flines)
        signal_dict = {}
        for ti in mi['port']:
            signal_dict[ti['name']] = ti
        for ti in mi['signal']:
            signal_dict[ti['name']] = ti
        # print ('Signal Dict = ' + str(signal_dict))
        signal_dict_text = ''
        for (name,ti) in signal_dict.items():
            signal_dict_text += name+'\n'
        # print ('Signal Dict = ' + signal_dict_text)
        # Add signal declaration
        for p in pm['port']:
            pname = p['name']
            #Remove suffix/prefix of port name
            for prefix in port_prefix:
                if pname.startswith(prefix):
                    pname = pname[len(prefix):]
                    break
            for suffix in port_suffix:
                if pname.endswith(suffix):
                    pname = pname[:-len(suffix)]
                    break
            if pname!=p['name']:
                ac[p['name']] = pname
            #check existing signal declaration and coherence
            ti = {'decl':None,'type':None,'array':"",'bw':"", 'name':pname, 'tag':''}
            if pname in signal_dict:
                ti = signal_dict[pname]
            # ti = verilogutil.get_type_info(flines,pname)
            # print ("Port " + p['name'] + " => " + pname + " => " + str(ti))

            # Check for extended match : prefix
            if ti['decl'] is None:
                if settings.get('sv.autoconnect_allow_prefix',False):
                    sl = re.findall(r'\b(\w+)_'+pname+r'\b', signal_dict_text, flags=re.MULTILINE)
                    if sl :
                        # print('Found signals for port ' + pname + ' with matching prefix: ' + str(set(sl)))
                        sn = sl[0] + '_' + pname # select first by default
                        for s in set(sl):
                            if s in pm['name']:
                                sn = s+'_' +pname
                                break;
                        if sn in signal_dict:
                            ti = signal_dict[sn]
                        # ti = verilogutil.get_type_info(flines,sn)
                        # print('Selecting ' + sn + ' with type ' + str(ti))
                        if ti['decl'] is not None:
                            ac[p['name']] = sn
            # Check for extended match : suffix
            if ti['decl'] is None:
                if settings.get('sv.autoconnect_allow_suffix',False):
                    sl = re.findall(r'\b'+pname+r'_(\w+)', signal_dict_text, flags=re.MULTILINE)
                    if sl :
                        # print('Found signals for port ' + pname + ' with matching suffix: ' + str(set(sl)))
                        sn = pname+'_' + sl[0] # select first by default
                        for s in set(sl):
                            if s in pm['name']:
                                sn = pname+'_' + s
                                break;
                        if sn in signal_dict:
                            ti = signal_dict[sn]
                        # ti = verilogutil.get_type_info(flines,sn)
                        # print('Selecting ' + sn + ' with type ' + str(ti))
                        if ti['decl'] is not None:
                            if sn != p['name']:
                                ac[p['name']] = sn
                            elif p['name'] in ac.keys():
                                ac.pop(p['name'],None)
            # Get declaration of signal for connecteion
            if p['decl'] :
                d = re.sub(r'input |output |inout ','',p['decl']) # remove I/O indication
                d = re.sub(r'var ','',d) # remove var indication
                if p['type'].startswith(('input','output','inout')) :
                    d = sig_type + ' ' + d
                elif '.' in d: # For interface remove modport and add instantiation. (No support for autoconnection of interface)
                    d = re.sub(r'(\w+)\.\w+\s+(.*)',r'\1 \2()',d)
                # If no signal is found, add declaration
                if ti['decl'] is None:
                    # print ("Adding declaration for " + pname + " => " + str(p['decl'] + ' => ' + d))
                    decl += indent_level*'\t' + d + ';\n'
                # Else check signal coherence
                else :
                    # Check port direction
                    if ti['decl'].startswith('input') and not p['decl'].startswith('input'):
                        wc[p['name']] = 'Incompatible port direction (not an input)'
                    # elif ti['decl'].startswith('output') and not p['decl'].startswith('output'):
                    #     wc[p['name']] = 'Incompatible port direction (not an output)'
                    elif ti['decl'].startswith('inout') and not p['decl'].startswith('inout'):
                        wc[p['name']] = 'Incompatible port direction not an inout'
                    # check type
                    ds = re.sub(r'input |output |inout ','',ti['decl']) # remove I/O indication
                    ds = re.sub(r'var |signed |unsigned ','',ds.strip()) # remove qualifier like var, signedm unsigned indication
                    d  = re.sub(r'signed |unsigned ','',d) # remove qualifier like var, signedm unsigned indication
                    d = re.sub(r'\(|\)','',d) # remove () for interface
                    if ti['type'].startswith(('input','output','inout')) :
                        ds = sig_type + ' ' + ds
                    elif '.' in ds: # For interface remove modport
                        ds = re.sub(r'(\w+)\b(.*)',r'\1',ds)
                        d = re.sub(r'(\w+)\b(.*)',r'\1',d)
                    # In case of smart autoconnect replace the signal name by the port name
                    if pname in ac.keys():
                        ds = re.sub(r'\b' + ac[p['name']] + r'\b', pname,ds)
                    if pname != p['name']:
                        ds = re.sub(r'\b' + pname + r'\b', p['name'],ds)
                    if ds!=d :
                        wc[p['name']] = 'Signal/port not matching : Expecting ' + d + ' -- Found ' + ds
                        wc[p['name']] = re.sub(r'\b'+p['name']+r'\b','',wc[p['name']]) # do not display port name
        return (decl,ac,wc)

##########################################
# Toggle between .* and explicit binding #
class VerilogToggleDotStarCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        r = self.view.sel()[0]
        scope = self.view.scope_name(r.a)
        if 'meta.module.inst' not in scope:
            return
        # Select whole module instantiation
        r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
        txt = verilogutil.clean_comment(self.view.substr(r))
        #Extract existing binding
        bl = re.findall(r'(?s)\.(\w+)\s*\(\s*(.*?)\s*\)',txt,flags=re.MULTILINE)
        #
        if '.*' in txt:
            # Parse module definition
            mname = re.findall(r'\w+',txt)[0]
            filelist = self.view.window().lookup_symbol_in_index(mname)
            if not filelist:
                return
            for f in filelist:
                fname = sublimeutil.normalize_fname(f[0])
                mi = verilogutil.parse_module_file(fname,mname)
                if mi:
                    break
            if not mi:
                return
            dot_star = ''
            b0 = [x[0] for x in bl]
            for p in mi['port']:
                if p['name'] not in b0:
                    dot_star += '.' + p['name']+'('+p['name']+'),\n'
            # select the .* and replace it (exclude the two last character which are ',\n')
            if dot_star != '' :
                r_tmp = self.view.find(r'\.\*',r.a)
                self.view.replace(edit,r_tmp,dot_star[:-2])
            else : # case where .* was superfluous (all bindings were manual) : remove .* including the potential ,
                r_tmp = self.view.find(r'\.\*\s*(,)?',r.a)
                self.view.erase(edit,r_tmp)
        else:
            # Find beginning of the binding and insert the .*
            r_begin = self.view.find(r'(\w+|\))\b\s*\w+\s*\(',r.a)
            if r.contains(r_begin):
                cnt = 0
                # erase all binding where port and signal have same name
                for b in bl:
                    if b[0]==b[1]:
                        cnt = cnt + 1
                        r_tmp = self.view.find(r'\.'+b[0]+r'\s*\(\s*' + b[0] + r'\s*\)\s*(,)?',r.a)
                        if r.contains(r_tmp):
                            self.view.erase(edit,r_tmp)
                            r_tmp = self.view.full_line(r_tmp.a)
                            m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
                            if m:
                                self.view.erase(edit,r_tmp)
                # Insert .* only if something was removed. Add , if not all binding were removed
                if cnt > 0:
                    if cnt==len(bl):
                        self.view.insert(edit,r_begin.b,'.*')
                    else :
                        self.view.insert(edit,r_begin.b,'.*,')
        self.view.run_command("verilog_align")


############################
# Do a module reconnection #
class VerilogModuleReconnectCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        r = self.view.sel()[0]
        scope = self.view.scope_name(r.a)
        if 'meta.module.inst' not in scope:
            return
        # Select whole module instantiation
        r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
        txt = verilogutil.clean_comment(self.view.substr(r))
        #Extract existing binding
        bl = re.findall(r'(?s)\.(\w+)\s*\(\s*(.*?)\s*\)',txt,flags=re.MULTILINE)
        # Parse module definition
        mname = re.findall(r'\w+',txt)[0]
        filelist = self.view.window().lookup_symbol_in_index(mname)
        if not filelist:
            return
        for f in filelist:
            fname = sublimeutil.normalize_fname(f[0])
            mi = verilogutil.parse_module_file(fname,mname)
            if mi:
                break
        if not mi:
            sublime.status_message('Unable to retrieve module information for ' + mname)
            return
        settings = self.view.settings()
        mpl = [x['name'] for x in mi['port']]
        ipl = [x[0] for x in bl]
        # Check for added port
        apl = [x for x in mpl if x not in ipl]
        if apl:
            (decl,ac,wc) = VerilogDoModuleInstCommand.get_connect(self, self.view, settings, mi)
            b = ''
            for p in apl:
                b+= "." + p + "("
                if p in ac.keys():
                    b+= ac[p]
                else :
                    b+= p
                b+= "),"
                if p in wc.keys():
                    b+=" // TODO: Check connection ! " + wc[p]
                b+="\n"
            # Add binding at the end of the instantiation
            self.view.insert(edit,r.b-2,b)
        # Check for deleted port
        dpl = [x for x in ipl if x not in mpl]
        for p in dpl:
            r_tmp = self.view.find(r'\.'+p+r'\s*\(.*?\)\s*(,)?',r.a)
            if r.contains(r_tmp):
                self.view.erase(edit,r_tmp)
                r_tmp = self.view.full_line(r_tmp.a)
                m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
                if m:
                    self.view.erase(edit,r_tmp)
        # Print status
        # print('[reconnect] Module   Port list = ' + str(mpl))
        # print('[reconnect] Instance Port list = ' + str(ipl))
        # print('[reconnect]  => Removed Port list = ' + str(dpl))
        # print('[reconnect]  => Added   Port list = ' + str(apl))
        s =''
        if dpl:
            s += "Removed %d ports: %s\n" %(len(dpl),str(dpl))
        if apl:
            s += "Added %d ports: %s\n" %(len(apl),str(apl))
            decl_clean = ''
            ac_clean = {}
            for p in apl:
                if p in ac:
                    ac_clean[p] = ac[p]
                if p in wc:
                    ac[p].pop()
                m = re.search(r'^.*\b'+p+r'\b.*;',decl, re.MULTILINE)
                if m:
                    decl_clean += m.group(0) +'\n'
            nb_decl = len(decl_clean.splitlines())
            if decl_clean:
                r = VerilogDoModuleInstCommand.get_region_decl(self, self.view,settings)
                self.view.insert(edit, r, '\n'+decl_clean)
                s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)\n'
            if len(ac_clean)>0 :
                s+= 'Non-perfect name match for ' + str(len(ac_clean)) + ' port(s) : ' + str(ac_clean) + '\n'
            if len(wc)>0 :
                s+= 'Found ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()]) +'\n'
        if s:
            sublimeutil.print_to_panel(s,'sv')
        # Realign
        self.view.run_command("verilog_align")
