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
            # read file to be able to check existing declaration
            flines = self.view.substr(sublime.Region(0, self.view.size()))
            # Add signal declaration
            for p in pm['port']:
                #check existing signal declaration and coherence
                ti = verilogutil.get_type_info(flines,p['name'])
                # print ("Port " + p['name'] + " => " + str(ti))
                if ti['decl'] is None:
                    # print ("Adding declaration for " + p['name'] + " => " + str(p['decl']))
                    if p['decl'] is None:
                        print("Unable to find proper declaration of port " + p['name'])
                    else:
                        d = re.sub(r'input |output |inout ','',p['decl']) # remove I/O indication
                        if p['type'].startswith(('input','output','inout')) :
                            d = sig_type + ' ' + d
                        decl += indent_level*'\t' + d + ';\n'
                #TODO: check signal coherence
                # else :
            #TODO: use self.view.settings().get('sv.decl_start') to know where to insert the declaration
            self.view.insert(edit, self.view.sel()[0].begin(), decl)
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
            max_len = max([len(x['name']) for x in pm['port']])
            for i in range(len(pm['port'])):
                inst+= "\t." + pm['port'][i]['name'].ljust(max_len) + "("
                if isAutoConnect:
                    inst+= pm['port'][i]['name'].ljust(max_len)
                inst+= ")"
                if i<len(pm['port'])-1:
                    inst+=","
                inst+="\n"
        inst += ");\n"
        self.view.insert(edit, self.view.sel()[0].begin(), inst)

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
        bl = re.findall(r'\.(\w+)\s*\(\s*(.*?)\s*\)',txt,flags=re.MULTILINE)
        #
        if '.*' in txt:
            # Parse module definition
            mname = re.findall(r'\w+',txt)[0]
            filelist = self.view.window().lookup_symbol_in_index(mname)
            if not filelist:
                return
            fname = sublimeutil.normalize_fname(filelist[0][0])
            mi = verilogutil.parse_module(fname,mname)
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