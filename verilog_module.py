import sublime, sublime_plugin
import re, string, os, sys, functools, mmap, imp

try:
    from SystemVerilog.verilogutil import verilogutil
    from SystemVerilog.verilogutil import sublimeutil
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
    import verilogutil
    import sublimeutil

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(sublimeutil)

list_module_files = {}
lmf_update_ongoing = False

########################################
def lookup_module(view,mname):
    mi = None
    filelist = view.window().lookup_symbol_in_index(mname)
    if filelist:
        for f in filelist:
            fname, display_fname, rowcol = f
            fname = sublimeutil.normalize_fname(fname)
            mi = verilogutil.parse_module_file(fname,mname)
            if mi:
                mi['fname'] = '{0}:{1}:{2}'.format(fname,rowcol[0],rowcol[1])
                break
    return mi

def lookup_function(view,funcname):
    fi = None
    filelist = view.window().lookup_symbol_in_index(funcname)
    if filelist:
        for f in filelist:
            fname, display_fname, rowcol = f
            fname = sublimeutil.normalize_fname(fname)
            with open(fname,'r') as f:
                flines = str(f.read())
            fi = verilogutil.parse_function(flines,funcname)
            if fi:
                fi['fname'] = '{0}:{1}:{2}'.format(fname,rowcol[0],rowcol[1])
                break
    return fi

def lookup_type(view, t):
    ti = None
    filelist = view.window().lookup_symbol_in_index(t)
    if filelist:
        for f in filelist:
            fname, display_fname, rowcol = f
            fname = sublimeutil.normalize_fname(fname)
            # Parse only systemVerilog file. Check might be a bit too restrictive ...
            # print(t + ' defined in ' + str(fname))
            if fname.lower().endswith(('sv','svh')):
                # print(t + ' defined in ' + str(fname))
                with open(fname, 'r') as f:
                    flines = str(f.read())
                ti = verilogutil.get_type_info(flines,t)
                if ti['type']:
                    ti['fname'] = '{0}:{1}:{2}'.format(fname,rowcol[0],rowcol[1])
                    break
    return ti

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
        self.window.show_quick_panel(list_module_files[projname], functools.partial(self.on_select_file_done,projname))

    def on_select_file_done(self, projname, index):
        if index >= 0:
            fname = list_module_files[projname][index]
            with open(fname, "r") as f:
                flines = str(f.read())
            self.ml=re.findall(r'^\s*module\s+(\w+)',flines,re.MULTILINE);
            if len(self.ml)<2:
                self.view.run_command("verilog_do_module_parse", {"args":{'fname': fname, 'mname':r'\w+'}})
            else:
                sublime.set_timeout_async(lambda: self.window.show_quick_panel(self.ml, functools.partial(self.on_select_module_done,fname)),0)

    def on_select_module_done(self, fname, index):
        if index >= 0:
            self.view.run_command("verilog_do_module_parse", {"args":{'fname': fname, 'mname':self.ml[index]}})

class VerilogDoModuleParseCommand(sublime_plugin.TextCommand):

    def run(self, edit, args):
        self.fname = args['fname']
        #TODO: check for multiple module in the file
        self.pm = verilogutil.parse_module_file(self.fname, args['mname'])
        self.param_explicit = self.view.settings().get('sv.param_explicit',False)
        self.param_propagate = self.view.settings().get('sv.param_propagate',False)
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
        elif self.param_explicit :
            self.param_value.append({'name':self.pm['param'][self.cnt]['name'] , 'value': content[9:]});
        self.cnt += 1
        if not self.pm['param']:
            return
        if self.cnt < len(self.pm['param']):
            self.show_prompt()
        else:
            self.view.run_command("verilog_do_module_inst", {"args":{'pm':self.pm, 'pv':self.param_value, 'text':self.fname}})

    def show_prompt(self):
        p = self.pm['param'][self.cnt]
        if self.param_propagate:
            default = 'parameter '
            if p['decl']:
                default += p['decl'] + ' '
            default += '{0} = {1}'.format(p['name'],p['value'])
        else:
            default = 'Default: {0}'.format(p['value'])
        panel = sublime.active_window().show_input_panel(p['name'], default, self.on_prompt_done, None, None)
        #select the whole line (to ease value change)
        r = panel.line(panel.sel()[0])
        panel.sel().clear()
        panel.sel().add(r)


class VerilogDoModuleInstCommand(sublime_plugin.TextCommand):
    #TODO: check base indentation
    def run(self, edit, args):
        settings = self.view.settings()
        isAutoConnect = settings.get('sv.autoconnect',False)
        isParamOneLine = settings.get('sv.param_oneline',True)
        isInstOneLine = settings.get('sv.inst_oneline',True)
        indent_level = settings.get('sv.decl_indent')
        param_decl = ''
        pm = args['pm']
        # print(pm)
        # Update Module information with parameter value for later signal declaration using correct type
        for p in args['pv']:
            for pmp in pm['param']:
                if pmp['name']==p['name']:
                    if p['value'].startswith('parameter') or p['value'].startswith('localparam'):
                        pmp['value']= p['name']
                        param_decl +=  indent_level*'\t' + p['value'] + ';\n'
                        m = re.search(r"(?P<name>\w+)\s*=",p['value'])
                        p['value'] = m.group('name')
                    else:
                        pmp['value']=p['value']
                    break
        # print('[VerilogDoModuleInstCommand] pm = '+ str(pm))
        decl = ''
        ac = {}
        wc = {}
        # Add signal port declaration
        if isAutoConnect and pm['port']:
            (decl,ac,wc) = self.get_connect(self.view, settings, pm)
            #Find location where to insert signal declaration: default to just before module instantiation
            if decl or param_decl:
                r = self.get_region_decl(self.view,settings)
                self.view.insert(edit, r, '\n'+param_decl+decl)
                sublime.status_message('Adding ' + str(len(decl.splitlines())) + ' signals declaration' )
        inst_name = settings.get('sv.instance_prefix','') + pm['name'] + settings.get('sv.instance_suffix','')
        # Check if instantiation can fit on one line only
        if isInstOneLine :
            len_inst = len(pm['name']) + 1 + len(inst_name) + 2
            if len(args['pv']) > 0:
                len_inst += 2
                for p in args['pv']:
                    len_inst += len(p['name']) + len(p['value']) + 5
            if len_inst+3 > settings.get('sv.max_line_length',120):
                isParamOneLine = False
            elif pm['port']:
                for p in pm['port']:
                    len_inst += len(p['name']) + 5
                    if p['name'] in ac.keys():
                        len_inst+= len(ac[p['name']])
                    else :
                        len_inst+= len(p['name'])
            if len_inst+3 > settings.get('sv.max_line_length',120):
                isInstOneLine = False
        # Instantiation
        inst = pm['name'] + " "
        # Parameters: bind only parameters for which a value different from default was set
        if len(args['pv']) > 0:
            if isParamOneLine:
                max_len = 0
            else:
                max_len = max([len(x['name']) for x in args['pv']])
            inst += "#("
            if not isParamOneLine:
                inst += "\n"
            for i in range(len(args['pv'])):
                if not isParamOneLine:
                    inst += "\t"
                inst+= "." + args['pv'][i]['name'].ljust(max_len) + "("+args['pv'][i]['value']+")"
                if i<len(args['pv'])-1:
                    inst+=","
                if not isParamOneLine:
                    inst+="\n"
                elif i<len(args['pv'])-1:
                    inst+=" "
            inst += ") "
        #Port binding
        inst +=  inst_name + " ("
        if not isInstOneLine:
             inst+="\n"
        if pm['port']:
            # Get max length of a port to align everything
            if isInstOneLine:
                max_len_p = 0
                max_len_s = 0
            else :
                max_len_p = max([len(x['name']) for x in pm['port']])
                max_len_s = max_len_p
            # print('Autoconnect dict = ' + str([ac[x] for x in ac]))
                if len(ac)>0 :
                    max_len_s = max([len(ac[x]) for x in ac])
                    if max_len_p>max_len_s:
                        max_len_s = max_len_p
            for i in range(len(pm['port'])):
                portname = pm['port'][i]['name']
                if not isInstOneLine:
                    inst += "\t"
                inst+= "." + portname.ljust(max_len_p) + "("
                if isAutoConnect:
                    if portname in ac.keys():
                        inst+= ac[portname].ljust(max_len_s)
                    else :
                        inst+= portname.ljust(max_len_s)
                inst+= ")"
                if i<len(pm['port'])-1:
                    inst+=","
                if not isInstOneLine:
                    if portname in wc.keys():
                        inst+=" // TODO: Check connection ! " + wc[portname]
                    inst+="\n"
                elif i<len(pm['port'])-1:
                    inst+=" "
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

    def get_region_decl(self, view, settings, r=None):
        if not r:
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
        port_prefix = settings.get('sv.autoconnect_port_prefix', [])
        port_suffix = settings.get('sv.autoconnect_port_suffix', [])
        indent_level = settings.get('sv.decl_indent', 1)
        #default signal type to logic, except verilog file use wire (if type is implicit)
        fname = view.file_name()
        sig_type = 'logic'
        if fname: # handle case where view is a scracth buffer and has no filename
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
        if pm['param']:
            param_dict = {p['name']:p['value'] for p in pm['param']}
        else:
            param_dict = {}
        # print(param_dict)
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
                for (k,v) in param_dict.items():
                    if k in d:
                        d = re.sub(r'\b'+k+r'\b',v,d)
                # try to cleanup the array size: [16-1:0] should give a proper [15:0]
                # Still very basic, but should be ok for most cases
                fa = re.findall(r'((\[|:)\s*(\d+)\s*(\+|-)\s*(\d+))',d)
                for f in fa:
                    if f[3]=='+':
                        value = int(f[2])+int(f[4])
                    else:
                        value = int(f[2])-int(f[4])
                    d = d.replace(f[0],f[1]+str(value))
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
                    # remove qualifier like var, signed, unsigned indication
                    ds = re.sub(r'var |signed |unsigned ','',ds.strip())
                    d  = re.sub(r'signed |unsigned ','',d)
                    # remove () for interface
                    d = re.sub(r'\(|\)','',d)
                    if ti['type'].startswith(('input','output','inout')) :
                        ds = sig_type + ' ' + ds
                    elif '.' in ds: # For interface remove modport
                        ds = re.sub(r'(\w+)\b(.*)',r'\1',ds)
                        d = re.sub(r'(\w+)\b(.*)',r'\1',d)
                    # convert wire/reg to logic
                    ds = re.sub(r'\b(wire|reg)\b','logic',ds.strip())
                    d  = re.sub(r'\b(wire|reg)\b','logic',d.strip())
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
        if self.view.classify(r.a) & sublime.CLASS_LINE_START == 0:
            r.a = self.view.find_by_class(r.a,False,sublime.CLASS_LINE_START)
        # print(self.view.substr(r))
        txt = verilogutil.clean_comment(self.view.substr(r))
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
        mpal = [x['name'] for x in mi['param']]
        #Extract existing binding
        bl = re.findall(r'(?s)\.(\w+)\s*\(\s*(.*?)\s*\)',txt,flags=re.MULTILINE)
        # Handle case of binding by position (TODO: support parameter as well ...)
        if not bl:
            m = re.search(r'(?s)(#\s*\((?P<params>.*)\)\s*)?\((?P<ports>.*)\)\s*;',txt,flags=re.MULTILINE)
            pl = m.group('ports')
            if pl:
                pa = pl.split(',')
                bt = ''
                for i,p in enumerate(pa):
                    if i >= len(mpl):
                        break;
                    bl.append((mpl[i],p.strip()))
                    bt += '.{portName}({sigName}),\n'.format(portName=bl[-1][0], sigName=bl[-1][1])
                # Replace connection by position by connection by name
                r_tmp = self.view.find(pl,r.a,sublime.LITERAL)
                if r.contains(r_tmp):
                    self.view.replace(edit,r_tmp,bt)
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
        dpl = [x for x in ipl if x not in mpl and x not in mpal]
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
                r_start = VerilogDoModuleInstCommand.get_region_decl(self, self.view,settings,r.a)
                self.view.insert(edit, r_start, '\n'+decl_clean)
                s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)\n'
            if len(ac_clean)>0 :
                s+= 'Non-perfect name match for ' + str(len(ac_clean)) + ' port(s) : ' + str(ac_clean) + '\n'
            if len(wc)>0 :
                s+= 'Found ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()]) +'\n'
        if s:
            sublimeutil.print_to_panel(s,'sv')
        # Realign
        self.view.run_command("verilog_align")
