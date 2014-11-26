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
            if r:
                # print("Found input at " + str(r) + ': ' + self.view.substr(self.view.line(r)))
                self.move_cursor(r)
                return
        # look for a connection explicit, implicit or by position
        sl = [r'\.(\w+)\s*\(\s*'+v+r'\b' , r'(\.\*)', r'(\(|,)\s*'+v+r'\b\s*(,|\))']
        for k,s in enumerate(sl):
            pl = []
            rl = self.view.find_all(s,0,r'$1',pl)
            for i,r in enumerate(rl):
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
                        mi = verilogutil.parse_module(fname,mname)
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
                                        self.move_cursor(r)
                                        return
                        if portname != '' :
                            op += portname+r'\b'
                            for x in mi['port']:
                                m = re.search(op,x['decl'])
                                if m:
                                    self.move_cursor(r)
                                    return

        # Everything failed
        sublime.status_message("Could not find driver of " + v)

    def move_cursor(self,r):
        r.a = r.a + 1
        r.b = r.a
        self.view.sel().clear()
        self.view.sel().add(r)
        self.view.show(r.a)


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
        self.pm = verilogutil.parse_module(self.fname)
        if self.pm is not None:
            self.param_value = []
            if self.pm['param'] is not None and self.view.settings().get('sv.fillparam'):
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
        isAutoConnect = self.view.settings().get('sv.autoconnect')
        # pm = verilogutil.parse_module(args['text'])
        pm = args['pm']
        # Add signal port declaration
        if isAutoConnect and pm['port'] is not None:
            decl = ""
            fname = self.view.file_name()
            indent_level = self.view.settings().get('sv.decl_indent')
            #default signal type to logic, except verilog file use wire (if type is implicit)
            sig_type = 'logic'
            if fname.endswith('.v'):
                sig_type = 'wire'
            ac = {}
            # read file to be able to check existing declaration
            flines = self.view.substr(sublime.Region(0, self.view.size()))
            # Add signal declaration
            for p in pm['port']:
                #check existing signal declaration and coherence
                ti = verilogutil.get_type_info(flines,p['name'])
                # print ("Port " + p['name'] + " => " + str(ti))
                # Check for extended match : prefix
                if ti['decl'] is None:
                    if self.view.settings().get('sv.autoconnect_allow_prefix',False):
                        sl = re.findall(r'\b(\w+)_'+p['name']+r'\b', flines, flags=re.MULTILINE)
                        if sl :
                            # print('Found signals for port ' + p['name'] + ' with matching prefix: ' + str(set(sl)))
                            sn = sl[0] + '_' + p['name'] # select first by default
                            for s in set(sl):
                                if s in pm['name']:
                                    sn = s+'_' +p['name']
                                    break;
                            ti = verilogutil.get_type_info(flines,sn)
                            # print('Selecting ' + sn + ' with type ' + str(ti))
                            if ti['decl'] is not None:
                                ac[p['name']] = sn
                # Check for extended match : suffix
                if ti['decl'] is None:
                    if self.view.settings().get('sv.autoconnect_allow_suffix',False):
                        sl = re.findall(r'\b'+p['name']+r'_(\w+)', flines, flags=re.MULTILINE)
                        if sl :
                            # print('Found signals for port ' + p['name'] + ' with matching suffix: ' + str(set(sl)))
                            sn = p['name']+'_' + sl[0] # select first by default
                            for s in set(sl):
                                if s in pm['name']:
                                    sn = p['name']+'_' + s
                                    break;
                            ti = verilogutil.get_type_info(flines,sn)
                            # print('Selecting ' + sn + ' with type ' + str(ti))
                            if ti['decl'] is not None:
                                ac[p['name']] = sn
                if ti['decl'] is None:
                    # print ("Adding declaration for " + p['name'] + " => " + str(p['decl']))
                    if p['decl'] is None:
                        print("Unable to find proper declaration of port " + p['name'])
                    else:
                        d = re.sub(r'input |output |inout ','',p['decl']) # remove I/O indication
                        if p['type'].startswith(('input','output','inout')) :
                            d = sig_type + ' ' + d
                        elif '.' in d: # For interface remove modport and add instantiation. (No support for autoconnection of interface)
                            d = re.sub(r'(\w+)\.\w+\s+(.*)',r'\1 \2()',d)
                        decl += indent_level*'\t' + d + ';\n'
                #TODO: check signal coherence
                # else :
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
                self.view.insert(edit, r, decl)
                sublime.status_message('Adding ' + str(len(decl.splitlines())) + ' signals declaration' )
        # Instantiation
        inst = pm['name'] + " "
        # Parameters: bind only parameters for which a value different from default was set
        if len(args['pv']) > 0:
            max_len = max([len(x['name']) for x in args['pv']])
            inst += "#(\n"
            for i in range(len(args['pv'])):
                inst+= "\t." + args['pv'][i]['name'].ljust(max_len) + "("+args['pv'][i]['value']+")"
                if i<len(pm['param'])-1:
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
                inst+="\n"
        inst += ");\n"
        self.view.insert(edit, self.view.sel()[0].a, inst)

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
                mi = verilogutil.parse_module(fname,mname)
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