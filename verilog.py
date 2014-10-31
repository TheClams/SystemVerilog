import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
import verilogutil

# Display type of the signal/variable under the cursor into the status bar
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region)
        s = self.get_type(v)
        if s is None:
            s = "No definition found for " + v
        sublime.status_message(s)

    def get_type(self,var_name):
        #Find first line containing the variable declaration
        r = self.view.find(verilogutil.re_decl+var_name+r'\b',0)
        if r==None : return ;
        l = self.view.substr(self.view.line(r))
        # Extract type
        ti = verilogutil.get_type_info(l,var_name)
        # print(ti)
        return ti[0]

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

class VerilogAutoComplete(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        # don't change completion if we are not in a systemVerilog file or we are inside a word
        if not view.match_selector(locations[0], 'source.systemverilog') or prefix!="" :
            return []
        # Get previous character anc check if it is a .
        r = view.sel()[0]
        r.a -=1
        t = view.substr(r)
        # print ("previous character: " + t)
        if t!='.':
            return []
        # select word before the dot and quit with no completion if no word found
        r.a -=1
        r.b = r.a
        r = view.word(r);
        v = str.rstrip(view.substr(r))
        # print ("previous word: " + v)
        if v=="":
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        # get type information on the variable
        r = view.find(verilogutil.re_decl+v+r'\b',0)
        if r==None :
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        ti = verilogutil.get_type_info(view.substr(view.line(r)),v)
        # print ("Type info: " + str(ti))
        if ti[0]==None:
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        completion = []
        #Provide completion for different type
        if ti[2]!="None" :
            completion = self.array_completion(ti[2])
        elif ti[1]=="string":
            completion = self.string_completion()
        elif ti[1]=="mailbox":
            completion = self.mailbox_completion()
        elif ti[1]=="semaphore":
            completion = self.semaphore_completion()
        #TODO: Provides more completion
        #Add randomize function for rand variable
        if ti[0].startswith("rand"):
            completion.append(["randomize()","randomize()"])
        return (completion, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    def array_completion(self,array_type):
        c = []
        if array_type == "queue":
            c.append(["size()"      ,"size()"])
            c.append(["insert()"    ,"insert()"])
            c.append(["delete()"    ,"delete()"])
            c.append(["pop_front()" ,"pop_front()"])
            c.append(["pop_back()"  ,"pop_back()"])
            c.append(["push_front()","push_front()"])
            c.append(["push_back()" ,"push_back()"])
        elif array_type == "associative":
            c.append(["num()"   ,"num()"])
            c.append(["size()"  ,"size()"])
            c.append(["delete()","delete()"])
            c.append(["exists()","exists()"])
            c.append(["first()" ,"first()"])
            c.append(["last()"  ,"last()"])
            c.append(["next()"  ,"next()"])
            c.append(["prev()"  ,"prev()"])
        else : # Fixed or dynamic have the same completion
           c.append(["size()","size()"])
           c.append(["find()","find(x) with(x)"])
           c.append(["find_index()","find_index(x) with (x)"])
           c.append(["find_first()","find_first(x) with (x)"])
           c.append(["find_last()","find_last(x) with (x)"])
           c.append(["unique()","unique()"])
           c.append(["uniques()","uniques(x) with(x)"])
           c.append(["reverse()","reverse()"])
           c.append(["sort()","sort()"])
           c.append(["rsort()","rsort()"])
           c.append(["shuffle()","shuffle()"])
        # Method available to all types of array
        c.append(["min()","min()"])
        c.append(["max()","max()"])
        c.append(["sum()","sum()"])
        c.append(["product()","product()"])
        c.append(["and()","and()"])
        c.append(["or()","or()"])
        c.append(["xor()","xor()"])
        return c

    def string_completion(self):
        c = []
        c.append(["len()"      , "len()"     ])
        c.append(["substr()"   , "substr()"  ])
        c.append(["putc()"     , "putc()"    ])
        c.append(["getc()"     , "getc()"    ])
        c.append(["toupper()"  , "toupper()" ])
        c.append(["tolower()"  , "tolower()" ])
        c.append(["compare()"  , "compare()" ])
        c.append(["icompare()" , "icompare()"])
        c.append(["atoi()"     , "atoi()"    ])
        c.append(["atohex()"   , "atohex()"  ])
        c.append(["atobin()"   , "atobin()"  ])
        c.append(["atoreal()"  , "atoreal()" ])
        c.append(["itoa()"     , "itoa()"    ])
        c.append(["hextoa()"   , "hextoa()"  ])
        c.append(["octoa()"    , "octoa()"   ])
        c.append(["bintoa()"   , "bintoa()"  ])
        c.append(["realtoa()"  , "realtoa()" ])
        return c

    def mailbox_completion(self):
        c = []
        c.append(["num()"      , "num()"     ])
        c.append(["get()"      , "get()"     ])
        c.append(["try_get()"  , "try_get()" ])
        c.append(["peek()"     , "peek()"    ])
        c.append(["try_peek()" , "try_peek()"])
        c.append(["put()"      , "put()"     ])
        c.append(["try_put()"  , "try_put()" ])
        return c

    def semaphore_completion(self):
        c = []
        c.append(["get()"      , "get()"     ])
        c.append(["try_get()"  , "try_get()" ])
        c.append(["put()"      , "put()"     ])
        return c