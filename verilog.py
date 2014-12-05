import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
import verilogutil
import sublimeutil

############################################################################
# Display type of the signal/variable under the cursor into the status bar #
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region)
        region = self.view.line(region)
        s = self.get_type(v,region.b)
        if s is None:
            s = "No definition found for " + v
        sublime.status_message(s)

    def get_type(self,var_name,pos):
        # select whole file
        txt = self.view.substr(sublime.Region(0, pos))
        # Extract type
        ti = verilogutil.get_type_info(txt,var_name)
        # print(ti)
        return ti['decl']

###################################################################
# Move cursor to the declaration of the signal currently selected #
class VerilogGotoDeclarationCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region).strip()
        sl = [verilogutil.re_decl + v + r'\b', verilogutil.re_enum + v + r'\b', verilogutil.re_union + v + r'\b', verilogutil.re_inst + v + '\b']
        for s in sl:
            r = self.view.find(s,0)
            if r:
                sublimeutil.move_cursor(self.view,r.b-1)
                return

############################################################################
# Move cursor to the driver of the signal currently selected #
class VerilogGotoDriverCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region).strip()
        # look for an input or an interface of the current module, and for an assignement
        sl = [r'\s*input\s+(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:]*\s+)?(\[[\w\:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?' + v + r'\b']
        sl.append(r'^\s*\w+\.\w+\s+' + v + r'\b')
        sl.append(r'\b' + v + r'\b\s*<?\=[^\=]')
        for s in sl:
            r = self.view.find(s,0)
            # print('searching ' + s + ' => ' + str(r))
            if r:
                # print("Found input at " + str(r) + ': ' + self.view.substr(self.view.line(r)))
                sublimeutil.move_cursor(self.view,r.a)
                return
        # look for a connection explicit, implicit or by position
        sl = [r'\.(\w+)\s*\(\s*'+v+r'\b' , r'(\.\*)', r'(\(|,)\s*'+v+r'\b\s*(,|\)\s*;)']
        for k,s in enumerate(sl):
            pl = []
            rl = self.view.find_all(s,0,r'$1',pl)
            # print('searching ' + s + ' => ' + str(rl))
            for i,r in enumerate(rl):
                # print('Found in line ' + self.view.substr(self.view.line(r)))
                # print('Scope for ' + str(r) + ' = ' + self.view.scope_name(r.a))
                if 'meta.module.inst' in self.view.scope_name(r.a) :
                    rm = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
                    txt = verilogutil.clean_comment(self.view.substr(rm))
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
                    if mi:
                        op = r'^(output\s+.*|\w+\.\w+\s+)'
                        # Output port string to search
                        portname = ''
                        if k==1:
                            portname = v
                        elif k==0:
                            portname = pl[i]
                        elif k==2 :
                            for j,l in enumerate(txt.split(',')) :
                                if v in l:
                                    dl = [x['decl'] for x in mi['port']]
                                    if re.search(op,dl[j]) :
                                        sublimeutil.move_cursor(self.view,r.a)
                                        return
                        if portname != '' :
                            op += portname+r'\b'
                            for x in mi['port']:
                                m = re.search(op,x['decl'])
                                if m:
                                    sublimeutil.move_cursor(self.view,r.a)
                                    return

        # Everything failed
        sublime.status_message("Could not find driver of " + v)


######################################################################################
# Create a new buffer showing the hierarchy (sub-module instances) of current module #
class VerilogShowHierarchyCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        txt = self.view.substr(sublime.Region(0, self.view.size()))
        txt = verilogutil.clean_comment(txt)
        mi = verilogutil.parse_module(txt,r'\b\w+\b')
        if not mi:
            print('[VerilogShowHierarchyCommand] Not inside a module !')
            return
        # Create Dictionnary where each type is associated with a list of tuple (instance type, instance name)
        self.d = {}
        top_level = mi['name']
        self.d[mi['name']] = [(x['type'],x['name']) for x in mi['inst']]
        li = [x['type'] for x in mi['inst']]
        while li:
            # print('Looping on list ' + str(li))
            li_next = []
            for i in li:
                if i not in self.d.keys():
                    # print('Parsing module ' + i)
                    filelist = self.view.window().lookup_symbol_in_index(i)
                    if not filelist:
                        break
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        mi = verilogutil.parse_module_file(fname,i)
                        if mi:
                            break
                    if mi:
                        li_next += [x['type'] for x in mi['inst']]
                        self.d[i] = [(x['type'],x['name']) for x in mi['inst']]
            li = li_next
        txt = top_level + '\n'
        txt += self.print_submodule(top_level,1)

        v = sublime.active_window().new_file()
        # print(str(self.d))
        v.run_command('insert_snippet',{'contents':str(txt)})

    def print_submodule(self,name,lvl):
        txt = ''
        if name in self.d:
            # print('print_submodule ' + str(self.d[name]))
            for x in self.d[name]:
                txt += '    '*lvl+'+ '+x[1].ljust(64)+'('+x[0]+')\n'
                # txt += '    '*lvl+'+ '+x[0]+' '+x[1]+'\n'
                txt += self.print_submodule(x[0],lvl+1)
        return txt

########################################
# Create module instantiation skeleton #
class VerilogModuleInstCommand(sublime_plugin.TextCommand):
    #TODO: Run the search in background and keep a cache to improve performance
    def run(self,edit):
        window = sublime.active_window()
        self.project_rtl = []
        for folder in window.folders():
            for root, dirs, files in os.walk(folder):
                for fn in files:
                    if os.path.splitext(fn)[1] in ['.v','.sv']:
                        self.project_rtl.append(os.path.join(root,fn))
        window.show_quick_panel(self.project_rtl, self.on_done )
        return

    def on_done(self, index):
        # print ("Selected: " + str(index) + " " + self.project_rtl[index])
        if index >= 0:
            self.view.run_command("verilog_do_module_parse", {"args":{'fname':self.project_rtl[index]}})

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
        port_prefix = settings.get('sv.autoconnect_port_prefix')
        port_suffix = settings.get('sv.autoconnect_port_suffix')
        # pm = verilogutil.parse_module_file(args['text'])
        pm = args['pm']
        # Add signal port declaration
        if isAutoConnect and pm['port']:
            decl = ""
            fname = self.view.file_name()
            indent_level = settings.get('sv.decl_indent')
            #default signal type to logic, except verilog file use wire (if type is implicit)
            sig_type = 'logic'
            if fname.endswith('.v'):
                sig_type = 'wire'
            ac = {} # autoconnection (entry is port name)
            wc = {} # warning connection (entry is port name)
            # read file to be able to check existing declaration
            flines = self.view.substr(sublime.Region(0, self.view.size()))
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
                ti = verilogutil.get_type_info(flines,pname)
                # print ("Port " + p['name'] + " => " + pname + " => " + str(ti))
                # Check for extended match : prefix
                if ti['decl'] is None:
                    if self.view.settings().get('sv.autoconnect_allow_prefix',False):
                        sl = re.findall(r'\b(\w+)_'+pname+r'\b', flines, flags=re.MULTILINE)
                        if sl :
                            # print('Found signals for port ' + pname + ' with matching prefix: ' + str(set(sl)))
                            sn = sl[0] + '_' + pname # select first by default
                            for s in set(sl):
                                if s in pm['name']:
                                    sn = s+'_' +pname
                                    break;
                            ti = verilogutil.get_type_info(flines,sn)
                            # print('Selecting ' + sn + ' with type ' + str(ti))
                            if ti['decl'] is not None:
                                ac[p['name']] = sn
                # Check for extended match : suffix
                if ti['decl'] is None:
                    if self.view.settings().get('sv.autoconnect_allow_suffix',False):
                        sl = re.findall(r'\b'+pname+r'_(\w+)', flines, flags=re.MULTILINE)
                        if sl :
                            # print('Found signals for port ' + pname + ' with matching suffix: ' + str(set(sl)))
                            sn = pname+'_' + sl[0] # select first by default
                            for s in set(sl):
                                if s in pm['name']:
                                    sn = pname+'_' + s
                                    break;
                            ti = verilogutil.get_type_info(flines,sn)
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
                        ds = re.sub(r'var |signed |unsigned ','',ds) # remove qualifier like var, signedm unsigned indication
                        d  = re.sub(r'signed |unsigned ','',d) # remove qualifier like var, signedm unsigned indication
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

            #Find location where to insert signal declaration: default to just before module instantiation
            if decl != "":
                r = self.view.sel()[0].begin()
                s = self.view.settings().get('sv.decl_start','')
                if s!='' :
                    r_start = self.view.find(s,0,sublime.LITERAL)
                    if r_start :
                        s = self.view.settings().get('sv.decl_end','')
                        r_stop = None
                        if s!='':
                            r_stop = self.view.find(s,r_start.a,sublime.LITERAL)
                        # Find first empty Find line
                        if r_stop:
                            r_tmp = self.view.find_by_class(r_stop.a,False,sublime.CLASS_EMPTY_LINE)
                        else :
                            r_tmp = self.view.find_by_class(r_start.a,True,sublime.CLASS_EMPTY_LINE)
                        if r_tmp:
                            r = r_tmp
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
        inst += self.view.settings().get('sv.instance_prefix') + pm['name'] + self.view.settings().get('sv.instance_suffix') + " (\n"
        if pm['port'] is not None:
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
            s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)'
        if len(ac)>0 :
            s+= '\nNon-perfect name match for ' + str(len(ac)) + ' port(s) : ' + str(ac)
        if len(wc)>0 :
            s+= '\nFound ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()])
        if s!='':
            sublimeutil.print_to_panel(s,'sv')


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
            r_tmp = self.view.find(r'(\w+|\))\b\s*\w+\s*\(',r.a)
            if r.contains(r_tmp):
                # todo: handle case where all binding are removed !
                self.view.insert(edit,r_tmp.b,'.*,')
                # erase all binding where port and signal have same name
                for b in bl:
                    if b[0]==b[1]:
                        # todo : check for comment to clean
                        r_tmp = self.view.find(r'\.'+b[0]+r'\s*\(\s*' + b[0] + r'\s*\)\s*(,)?',r.a)
                        if r.contains(r_tmp):
                            self.view.erase(edit,r_tmp)
                            r_tmp = self.view.full_line(r_tmp.a)
                            m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
                            if m:
                                self.view.erase(edit,r_tmp)

        self.view.run_command("verilog_align")