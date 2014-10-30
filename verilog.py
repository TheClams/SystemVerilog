import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
import verilogutil

# Display type of the signal/variable under the cursor into the status bar
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selction to word
        if region.empty() : region = self.view.word(region);
        s = self.get_type(self.view.substr(region))
        sublime.status_message(s)

    def get_type(self,var_name):
        #Find first line containing the variable name
        r = self.view.find('\\b'+var_name+'\\b',0)
        if r==None : return;
        r = self.view.line(r)
        # Extract type
        return self.view.substr(r)

# Create module instantiation skeleton
class VerilogModuleInstCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        window = sublime.active_window()
        self.project_rtl = []
        for folder in window.folders():
            for root, dirs, files in os.walk(folder):
                for fn in files:
                    if os.path.splitext(fn)[1] in ['.v','.sv']:
                        self.project_rtl.append(os.path.join(root,fn))
                        # self.project_rtl.append([fn,os.path.join(root,fn)])
        # print (window.project_data()['folders'][0]['path'])
        window.show_quick_panel(self.project_rtl, self.on_done )
        return

    def on_done(self, index):
        print (self.project_rtl[index])
        self.view.run_command("verilog_do_module_inst", {"args":{'text':self.project_rtl[index]}})

class VerilogDoModuleInstCommand(sublime_plugin.TextCommand):

    def run(self, edit, args):
        if len(self.view.sel())==0:
            return
        with open(args['text'], "r") as f:
            flines = str(f.read())
            #TODO: use a function verilogutil extracting properly module name, parameter, IO
            m = re.search("module\s+(\w+)\s*(#\s*\([^;]+\))?\s*\(([^;]+)\)\s*;", flines)
            if m is not None:
                # print("Found module ", m.groups()[0])
                inst = m.groups()[0] + " "
                if m.groups()[1] is not None:
                    param_str = verilogutil.clean_comment(m.groups()[1])
                    inst += "#(\n"
                    # print("      param = ", param_str)
                    params = re.findall(r"(\w+)\s*=",param_str)
                    if params is not None:
                        for i in range(len(params)):
                            inst+= "\t." + params[i] + "()"
                            if i<len(params)-1:
                                inst+=","
                            inst+="\n"
                        inst += ") "
                #TODO: add config for prefix/suffix
                inst += "i_" + m.groups()[0] + " (\n"
                if m.groups()[2] is not None:
                    port_str = verilogutil.clean_comment(m.groups()[2])
                    ports = re.findall(r"(\w+)\s*(,|$)",port_str)
                    if ports is not None:
                        for i in range(len(ports)):
                            inst+= "\t." + ports[i][0] + "()"
                            if i<len(ports)-1:
                                inst+=","
                            inst+="\n"
                inst += ");\n"
                self.view.insert(edit, self.view.sel()[0].begin(), inst)