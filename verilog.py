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
        return ti['decl']

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
        # print ("Selected: " + str(index) + " " + self.project_rtl[index])
        if index >= 0:
            self.view.run_command("verilog_do_module_parse", {"args":{'text':self.project_rtl[index]}})

class VerilogDoModuleParseCommand(sublime_plugin.TextCommand):

    def run(self, edit, args):
        # print ("Parsing " + args['text'])
        self.fname = args['text']
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
            # read file to be able to check existing
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
        if ti==None:
            return ([], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
        completion = []
        #Provide completion for different type
        if ti['array']!="None" :
            completion = self.array_completion(ti['array'])
        elif ti['type']=="string":
            completion = self.string_completion()
        elif ti['type']=="mailbox":
            completion = self.mailbox_completion()
        elif ti['type']=="semaphore":
            completion = self.semaphore_completion()
        #TODO: Provides more completion
        #Add randomize function for rand variable
        if ti['decl'].startswith("rand ") or " rand " in ti['decl']:
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