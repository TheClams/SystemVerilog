import sublime, sublime_plugin
import re, string, os, sys, imp, time, threading
import collections

from . import verilog_module
from .verilogutil import verilogutil
from .verilogutil import verilog_beautifier
from .verilogutil import sublimeutil

############################################################################

def plugin_loaded():
    r = threading.Thread(target=reload, daemon=True)
    r.start()

def reload():
    cnt = 3
    while cnt > 0:
        try:
            time.sleep(1)
            from . import verilog_module
            from .verilogutil import verilogutil, verilog_beautifier, sublimeutil
            imp.reload(verilogutil)
            imp.reload(verilog_beautifier)
            imp.reload(sublimeutil)
            imp.reload(verilog_module)
            # print('[SV] Completion Loaded')
            cnt = 0
        except:
            cnt -= 1
            time.sleep(2)



############################################################################
# Kind definition
MYKIND_KEYWORD  = (sublime.KIND_ID_KEYWORD , "k", "Keyword")
MYKIND_FUNCTION = (sublime.KIND_ID_FUNCTION, "f", "Function")
MYKIND_FIELD    = (sublime.KIND_ID_VARIABLE, "v", "Field")
MYKIND_MODPORT  = (sublime.KIND_ID_TYPE, "m", "Modport")
MYKIND_CLOCKING = (sublime.KIND_ID_NAMESPACE, "c", "Clocking")

############################################################################
class VerilogAutoComplete(sublime_plugin.EventListener):

    # Cache latest information
    cache_module = {'name' : '', 'date' : 0, 'info' : None}

    def on_query_completions(self, view, prefix, locations):
        # don't change completion if we are not in a systemVerilog file
        if not view.match_selector(locations[0], 'source.systemverilog'):
            return []
        self.view = view
        self.settings = view.settings()
        self.debug = self.settings.get("sv.debug")
        if self.settings.get("sv.disable_autocomplete"):
            if self.debug:
                print('[SV:on_query_completions] Autocompletion disabled')
            return []
        r = view.sel()[0]
        self.scope = view.scope_name(r.a)
        if('string' in self.scope) :
            return []
        # If there is a prefix, allow sublime to provide completion ?
        flag = 0
        if(prefix==''):
            flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
        # print(f'[SV:on_query_completions] "{prefix=}" {flag=}')
        # Extract previous character and whole line before prefix
        prev_symb = ''
        prev_word = ''
        prev_char = view.substr(sublime.Region(r.a-1,r.b))
        lr = sublime.Region(r.a,r.b)
        lr.a = view.find_by_class(lr.b,False,sublime.CLASS_LINE_START)
        l = view.substr(lr).strip()
        r.b -= len(prefix)
        r.a = r.b - 1
        tmp_r = sublime.Region(r.a,r.b)
        # print('[SV:on_query_completions] tmp_r={0} => "{1}" . Class = {2}, flag= {3}'.format(tmp_r,view.substr(tmp_r),view.classify(tmp_r.b),flag))
        if not view.substr(tmp_r).strip() :
            tmp_r.b = view.find_by_class(tmp_r.b,False,sublime.CLASS_LINE_START | sublime.CLASS_PUNCTUATION_END | sublime.CLASS_WORD_END)
            tmp_r.a = tmp_r.b
        if view.substr(tmp_r) in ['.','`','=','?']:
            prev_symb = view.substr(tmp_r)
        elif view.classify(tmp_r.b) & (sublime.CLASS_PUNCTUATION_END | 8192 | 4096):
            #print('[SV:on_query_completions] tmp_r={0} => "{1}" ==>'.format(tmp_r,view.substr(tmp_r)))
            tmp_r.a = view.find_by_class(tmp_r.b,False,sublime.CLASS_PUNCTUATION_START)
            prev_symb = view.substr(tmp_r).strip()
            if not prev_symb :
                tmp_r.b = view.find_by_class(tmp_r.a,False,sublime.CLASS_LINE_START | sublime.CLASS_PUNCTUATION_END | sublime.CLASS_WORD_END)
                tmp_r.a = tmp_r.b
            else:
                if prev_symb[-1] == '.':
                    prev_symb = '.'
                    tmp_r.a = tmp_r.b - 1
                tmp_r.b = tmp_r.a
        if view.classify(tmp_r.b) & sublime.CLASS_WORD_END:
            tmp_r.a = view.find_by_class(tmp_r.b,False,sublime.CLASS_WORD_START)
            prev_word = view.substr(tmp_r).strip()
            tmp_r.b = tmp_r.a
            # print('[SV:on_query_completions] (word end) tmp_r={0} => "{1}" '.format(tmp_r,view.substr(tmp_r)))
        # Extract only last character for some symbol (typically to handle a parenthesis just before the operator)
        if prev_symb and prev_symb[-1] in ['$','`','.']:
            prev_symb = prev_symb[-1]
        completion = []
        scope_tmp = view.scope_name(tmp_r.a)
        # if self.debug:
        # print('[SV:on_query_completions] prefix="{0}" previous symbol="{1}" previous word="{2}" char="{5}" line="{3}" scope={4}'.format(prefix,prev_symb,prev_word,l,self.scope,prev_char))
        # Select completion function
        if prev_symb=='$' or prefix.startswith('$'):
            # print('[SV:completion] ListBased - systemtask')
            flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
            completion = self.listbased_completion('systemtask')
        elif prev_symb=='`':
            # print('[SV:completion] Macro / Directive')
            pl = ''
            if prefix:
                _,pl = verilog_module.lookup_macro(self.view,prefix)
            if pl:
                pl = pl.split(',')
                s= '`{}('.format(prefix)
                for i,p in enumerate(pl):
                    s+= '${{{0}:{1}}}'.format(i+1,p.strip())
                    if i != (len(pl)-1):
                        s+=', '
                s+= ')${0}'
                completion.append(['`{}\tmacro'.format(prefix),s])
                flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
            else:
                completion =  self.listbased_completion('tick')
        elif prev_symb=='.':
            # print('[SV:completion] Dot')
            completion =  self.dot_completion(view,r)
            if completion is not None and len(completion) == 0:
                completion = None
        elif prev_symb=='::':
            if not prev_word:
                tmp_r.a = view.find_by_class(tmp_r.a,False,sublime.CLASS_WORD_START)
                prev_word = view.substr(tmp_r).strip()
            if prev_word:
                flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
            # print(f'[SV:completion] Scope of {prev_word}')
            completion =  self.scope_completion(view,prev_word)
        elif prev_symb.endswith(')'):
            # print('[SV:completion] Case ?')
            m = re.search(r'^\s*case\s*\((.+?)\)$',l)
            if m:
                completion = self.case_completion(m.groups()[0])
        # elif (prev_symb in ['?',':'] or '=' or prev_symb) and not prefix:
        # elif prev_symb in ['=','?',':'] and not prefix:
        elif (prev_symb in ['?',':'] or '=' in prev_symb):
            # print('[SV:completion] Enum Assign ?')
            if len(prefix)>0 and len(l)>len(prefix):
                flag = 0
                l = l[:-len(prefix)]
            m = re.search(r'(?P<name>[\w\.]+)\s*(?:<=|=|!=|==)=?(\s*|[^;]+?(\?|:)\s*)$',l)
            # print(f'[SV:completion] line = {l}')
            if m:
                completion = self.enum_assign_completion(view,m.group('name'))
        elif 'meta.struct.assign' in self.scope:
            # print('[SV:completion] Struct Assign')
            completion = self.struct_assign_completion(view,r,prev_symb==',')
        elif 'meta.block.cover.systemverilog' in self.scope and 'string' not in self.scope:
            # print('[SV:completion] Cover')
            completion = self.cover_completion()
        elif 'meta.block.constraint.systemverilog' in self.scope and 'meta.brackets' not in self.scope:
            # print('[SV:completion] Constraint')
            completion = self.constraint_completion()
        elif prefix:
            # print('[SV:completion] Other')
            symbols = {n:l for l,n in view.symbols()}
            l = ''
            if 'meta.function.prototype' in scope_tmp:
                # print('[SV:completion] Function Prototype -> no completion')
                return ([], 0)
            if prefix in symbols:
                tmp_r = view.line(symbols[prefix])
                l = view.substr(tmp_r)
            if 'function' in l:
                # print('[SV:completion] Function Snippet')
                flines = verilogutil.clean_comment(view.substr(sublime.Region(tmp_r.a,self.view.size())))
                fi = verilogutil.parse_function(flines,prefix)
                if fi :
                    s = self.function_snippet(fi)
                    completion.append([fi['name']+'\t'+fi['type'],s])
                    flag = 0
            # Provide completion for most used uvm function
            elif(prefix.startswith('u')):
                # print('[SV:completion] Function Snippet')
                completion =  self.listbased_completion('uvm')
            # Provide completion for most always block
            elif(prefix.startswith('a')):
                # print('[SV:completion] Always')
                completion = self.always_completion()
            # Provide completion for endfunction, endtask, endclass, endmodule, endpackage, endinterface
            elif(prefix.startswith('end')):
                # print('[SV:completion] End')
                completion = self.end_completion(view,r,prefix)
            # Provide simple keywords completion
            else:
                completion =  self.listbased_completion('core')
                if prefix.startswith('m') :
                    completion += self.modport_completion()
                # completion = [
                #     sublime.CompletionItem("generate","keyword","generate\n\t$0\nendgenerate" ,kind=sublime.KIND_SNIPPET, completion_format=1),
                #     sublime.CompletionItem("posedge","keyword" ,"posedge ",kind=MYKIND_KEYWORD),
                #     sublime.CompletionItem("negedge","keyword" ,"negedge ",kind=MYKIND_KEYWORD)
                # ]
        elif prev_symb.endswith(','):
            completion = None
        # print(f'[SV:on_query_completions] Nb completion = {len(completion)} | {flag=}')
        # if flag!=0 and isinstance(completion,list) and len(completion) == 0:
        #     completion = None
        # Ensure completion from sublime are available if there was a prefix
        if completion == None and (prefix != '' or prev_char.strip()==''):
            completion = []
        return (completion, flag)

    def always_completion(self):
        c = []
        (a_l,a_h,a_nr) = VerilogHelper.get_always_template(self.view)
        if self.settings.get('sv.always_label',True):
            begin_end = 'begin : proc_$0\n\nend'
        else:
            begin_end = 'begin\n\nend'
        #Provide completion specific to the file type
        fname = self.view.file_name()
        if fname:
            is_sv = fname.lower().endswith(tuple(self.settings.get('sv.sv_ext','sv')))
        else:
            is_sv = False
        if is_sv :
            c.append(sublime.CompletionItem('always_ff','always_ff Async','always_ff '+a_l,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_ffh','always_ff Async high','always_ff '+a_h,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_c','always_comb','always_comb '+ begin_end,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_l','always_latch','always_latch '+ begin_end,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_ff_nr','always_ff No reset','always_ff '+a_nr,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_ffs','always_ff Sync','always_ff '+re.sub(r' or negedge \w+','',a_l),kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_ffsh','always_ff Sync high','always_ff '+re.sub(r' or posedge \w+','',a_h),kind=sublime.KIND_SNIPPET, completion_format=1))
        if not is_sv or not self.settings.get('sv.always_sv_only') :
            c.append(sublime.CompletionItem('always','always Async','always '+a_l,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('alwaysh','always Async high','always '+a_h,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('alwaysc','always *','always @(*) '+ begin_end,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('always_nr','always NoReset','always_ff '+a_nr,kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('alwayss','always sync','always '+re.sub(r' or negedge \w+','',a_l),kind=sublime.KIND_SNIPPET, completion_format=1))
            c.append(sublime.CompletionItem('alwayssh','always sync high','always '+re.sub(r' or posedge \w+','',a_h),kind=sublime.KIND_SNIPPET, completion_format=1))
        return c

    def modport_completion(self):
        _,_,r = sublimeutil.find_closest(self.view,self.view.sel()[0],r'\binterface\b()')
        if not r:
            return []
        txt = self.view.substr(sublime.Region(r[-1].a,self.view.size()))
        ti = verilogutil.parse_module(txt,r'\w+')
        if not ti or ti['type'] != 'interface':
            return []
        modport = 'modport ${1:mp} ($0'
        for i,s in enumerate(ti['signal']):
            modport += s['name']
            if i!= len(ti['signal'])-1:
                modport += ', '
        modport += ');'
        # return [sublime.CompletionItem("modport","declaration","fork\n\t$0\njoin",kind=sublime.KIND_SNIPPET, completion_format=1)]
        return [['modport\tModport template',modport]]

    def dot_completion(self,view,r):
        # select word before the dot and quit with no completion if no word found
        start_pos = r.a # save original position of the .
        start_word = view.substr(view.word(r))
        r.b = r.a
        r.a -=1
        array_depth = 0

        # Handle array case
        while view.substr(r) == ']' :
            r.a -=1
            r.b = r.a
            while view.substr(r) != '[' :
                r.a = view.find_by_class(r.a,False,sublime.CLASS_PUNCTUATION_START)
                r.b = r.a + 1
            r.b = r.a
            r.a -=1
            array_depth += 1
        scope = view.scope_name(r.a)
        r = view.word(r)
        w = str.rstrip(view.substr(r))
        completion = []
        # print (f'[SV:dot_completion] previous word: {w}, {scope=}')
        if w == 'this':
            cname,_,_ = sublimeutil.find_closest(view,r,r'\bclass\s+(\w+)\b')
            if cname :
                txt = self.view.substr(sublime.Region(0,self.view.size()))
                return self.class_completion('',cname,txt,False)
        elif w == 'super':
            cname,_,_ = sublimeutil.find_closest(view,r,r'\bclass\s+.*?\bextends\s+(.*?);')
            if cname :
                if cname:
                    ci = verilog_module.lookup_type(self.view,cname)
                    if ci:
                        return self.class_completion(ci['fname'][0],cname,'',False)
        # Cover option completion
        elif w in ['option','type_option'] and 'meta.block.cover' in scope:
            completion.append(sublime.CompletionItem('weight','option','weight = $0;',kind=MYKIND_FIELD, completion_format=1))
            completion.append(sublime.CompletionItem('goal','option','goal = $0;',kind=MYKIND_FIELD, completion_format=1))
            completion.append(sublime.CompletionItem('comment','option','comment = "$0";',kind=MYKIND_FIELD, completion_format=1))
            if w=='option' :
                completion.append(sublime.CompletionItem('name','option','name = "$0";',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('at_least','option','at_least = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('detect_overlap','option','detect_overlap = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('auto_bin_max','option','auto_bin_max = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('cross_num_print_missing','option','cross_num_print_missing = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('per_instance','option','per_instance = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('get_inst_coverage','option','get_inst_coverage = $0;',kind=MYKIND_FIELD, completion_format=1))
            else :
                completion.append(sublime.CompletionItem('strobe','option','strobe = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('merge_instances','option','merge_instances = $0;',kind=MYKIND_FIELD, completion_format=1))
                completion.append(sublime.CompletionItem('distribute_first','option','distribute_first = $0;',kind=MYKIND_FIELD, completion_format=1))
            return completion
        #
        elif w=='' or not re.match(r'\w+',w) or start_word.startswith('(') or start_word.startswith('#'):
            #No word before dot => check the scope
            if 'meta.module.inst' in scope:
                r = sublimeutil.expand_to_scope(view,'meta.module.inst',r)
                txt = verilogutil.clean_comment(view.substr(r))
                words = re.findall(r'[\w\`][\w\.]*|`\w+',txt)
                if words[0]=='bind':
                    if len(words)<3:
                        print("[SV:dot_completion] Unable to get bind module name: expect 'bind inst_name module_name'")
                        return completion
                    mname = words[2]
                else:
                    mname = words[0]
                filelist = view.window().lookup_symbol_in_index(mname)
                if filelist:
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        mi = verilogutil.parse_module_file(fname,mname)
                        if mi:
                            break
                    is_param = 'meta.block.bind.param' in scope
                    # print (f'{scope=}')
                    completion = self.module_binding_completion(view.substr(r),txt, mi,start_pos-r.a,is_param)
            else :
                return completion
        else :
            fname = ''
            cdecl = ''
            modport_only = False
            # Check for multiple level of hierarchy
            cnt = 1
            autocomplete_max_lvl = self.settings.get("sv.autocomplete_max_lvl",4)
            while r.a>1 and self.view.substr(sublime.Region(r.a-1,r.a))=='.' and (cnt < autocomplete_max_lvl or autocomplete_max_lvl<0):
                if 'support.function.port' not in self.view.scope_name(r.a):
                    # check previous char for array selection
                    c = self.view.substr(sublime.Region(r.a-2,r.a-1))
                    # Array selection -> extend to start of array
                    if c == ']':
                        r.a = self.view.find_by_class(r.a-3,False,sublime.CLASS_WORD_START)
                        # print('[SV:dot_completion] Extending array selection -> {}'.format(view.substr(r)))
                    if self.view.classify(r.a-2) & sublime.CLASS_WORD_START:
                        r.a = r.a-2
                    else :
                        r.a = self.view.find_by_class(r.a-2,False,sublime.CLASS_WORD_START)
                cnt += 1
            if (cnt >= autocomplete_max_lvl and autocomplete_max_lvl>=0):
                print("[SV:dot_completion] Reached max hierarchy level for autocompletion. You can change setting sv.autocomplete_max_lvl")
                return completion
            w = str.rstrip(view.substr(r))
            # print('[SV:dot_completion] Word = {}'.format(w))
            # get type information on the variable
            txt = view.substr(sublime.Region(0, view.size()))
            ti = verilog_module.type_info_on_hier(view,w,txt,r)
            # print('[SV:dot_completion] Type = {}'.format(ti))
            if not ti or (ti['type'] is None and 'meta.module.port.systemverilog' not in scope):
                return completion
            #Provide completion for different type
            if ti['array']!='' and array_depth==0:
                completion = self.array_completion(ti['array'])
            elif ti['type']=='string':
                completion = self.string_completion()
            elif ti['type']=='enum':
                completion = self.enum_completion()
            elif ti['type']=='mailbox':
                completion = self.mailbox_completion()
            elif ti['type']=='semaphore':
                completion = self.semaphore_completion()
            elif ti['type']=='process':
                completion = self.process_completion()
            elif ti['type']=='event':
                completion.append(sublime.CompletionItem('triggered','event','triggered',kind=MYKIND_KEYWORD))
            # Non standard type => try to find the type in the lookup list and get the type
            else:
                # Force the type to the word itself if we are in a module declaration : typical of modport
                if ti['type'] is None and 'meta.module.port.systemverilog' in scope:
                    t = w
                    modport_only = True
                elif ti['type']=='module':
                    t = w
                elif ti['type']=='clocking':
                    for x in ti['port']:
                        completion.append(sublime.CompletionItem(x['name'],x['type'], x['name'],kind=MYKIND_FIELD))
                    return completion
                else:
                    t = ti['type']

                tti = None
                t = re.sub(r'\w+\:\:','',t) # remove scope from type. TODO: use the scope instead of rely on global lookup
                filelist = view.window().lookup_symbol_in_index(t)
                # print(' Filelist for ' + t + ' = ' + str(filelist))
                if filelist:
                    file_ext = tuple(self.settings.get('sv.v_ext','v') + self.settings.get('sv.sv_ext','sv') + self.settings.get('sv.vh_ext','vh') + self.settings.get('sv.svh_ext','svh'))
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        # Parse only verilog files. Check might be a bit too restrictive ...
                        if fname.lower().endswith(file_ext):
                            # print(w + ' of type ' + t + ' defined in ' + str(fname))
                            tti = verilog_module.type_info_file(view,fname,t)
                            # print(tti)
                            if tti['type']:
                                if tti['tag']=='typedef':
                                    tti = verilog_module.lookup_type(view,tti['type'])
                                    if tti:
                                        fname = tti['fname'][0]
                                break
                # print(tti)
                if not tti:
                    return None
                if tti['type']=='interface':
                    return self.interface_completion(fname,tti['name'], modport_only)
                elif tti['type'] == 'class':
                    return self.class_completion(fname,tti['name'])
                elif tti['type']=='enum':
                    completion = self.enum_completion()
                elif tti['type'] in ['struct','union']:
                    completion = self.struct_completion(tti['decl'])
                elif tti['type']=='module':
                    return self.module_completion(fname,tti['name'])
            #Add randomize function for rand variable
            if ti['decl']:
                if ti['decl'].startswith('rand ') or ' rand ' in ti['decl']:
                    completion.append(sublime.CompletionItem('randomize','randomize()','randomize()',kind=MYKIND_FUNCTION))
        return completion

    def array_completion(self,array_type):
        c = []
        if array_type == 'queue':
            c.append(sublime.CompletionItem('size','size()'            ,'size()'      ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('insert','insert()'        ,'insert()'    ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('delete','delete()'        ,'delete()'    ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('pop_front','pop_front()'  ,'pop_front()' ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('pop_back','pop_back()'    ,'pop_back()'  ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('push_front','push_front()','push_front()',kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('push_back','push_back()'  ,'push_back()' ,kind=MYKIND_FUNCTION))
        elif array_type == 'associative':
            c.append(sublime.CompletionItem('num','num()'      ,'num()'     ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('size','size()'    ,'size()'    ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('delete','delete()','delete()'  ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('exists','exists()','exists($0)',kind=MYKIND_FUNCTION, completion_format=1))
            c.append(sublime.CompletionItem('first','first()'  ,'first()'   ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('last','last()'    ,'last()'    ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('next','next()'    ,'next()'    ,kind=MYKIND_FUNCTION))
            c.append(sublime.CompletionItem('prev','prev()'    ,'prev()'    ,kind=MYKIND_FUNCTION))
        else : # Fixed or dynamic have the same completion
           c.append(sublime.CompletionItem('size','size()'                 ,'size()'                  ,kind=MYKIND_FUNCTION))
           c.append(sublime.CompletionItem('find','find() ...'             ,'find($1) with($0)'       ,kind=MYKIND_FUNCTION, completion_format=1))
           c.append(sublime.CompletionItem('find_index','find_index() ...' ,'find_index($1) with ($0)',kind=MYKIND_FUNCTION, completion_format=1))
           c.append(sublime.CompletionItem('find_first','find_first() ...' ,'find_first($1) with ($0)',kind=MYKIND_FUNCTION, completion_format=1))
           c.append(sublime.CompletionItem('find_last','find_last()'       ,'find_last($1) with ($0)' ,kind=MYKIND_FUNCTION, completion_format=1))
           c.append(sublime.CompletionItem('unique','unique()'             ,'unique()'                ,kind=MYKIND_FUNCTION))
           c.append(sublime.CompletionItem('uniques','unique() with ...'   ,'unique($1) with($0)'    ,kind=MYKIND_FUNCTION, completion_format=1))
           c.append(sublime.CompletionItem('reverse','reverse()'           ,'reverse()'               ,kind=MYKIND_FUNCTION))
           c.append(sublime.CompletionItem('sort','sort()'                 ,'sort()'                  ,kind=MYKIND_FUNCTION))
           c.append(sublime.CompletionItem('rsort','rsort()'               ,'rsort()'                 ,kind=MYKIND_FUNCTION))
           c.append(sublime.CompletionItem('shuffle','shuffle()'           ,'shuffle()'               ,kind=MYKIND_FUNCTION))
        # Method available to all types of array
        c.append(sublime.CompletionItem('min','min()'        ,'min()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('max','max()'        ,'max()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('sum','sum()'        ,'sum()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('product','product()','product()',kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('and','and()'        ,'and()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('or','or()'          ,'or()'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('xor','xor()'        ,'xor()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def string_completion(self):
        c = []
        c.append(sublime.CompletionItem('len','len()'          , 'len()'        ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('substr','substr()'    , 'substr($1,$0)',kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('putc','putc()'        , 'putc($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('getc','getc()'        , 'getc($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('toupper','toupper()'  , 'toupper()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('tolower','tolower()'  , 'tolower()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('compare','compare()'  , 'compare($0)'  ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('icompare','icompare()', 'icompare($0)' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('atoi','atoi()'        , 'atoi()'       ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('atohex','atohex()'    , 'atohex()'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('atobin','atobin()'    , 'atobin()'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('atoreal','atoreal()'  , 'atoreal()'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('itoa','itoa()'        , 'itoa($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('hextoa','hextoa()'    , 'hextoa($0)'   ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('octoa','octoa()'      , 'octoa($0)'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('bintoa','bintoa()'    , 'bintoa($0)'   ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('realtoa','realtoa()'  , 'realtoa($0)'  ,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def mailbox_completion(self):
        c = []
        c.append(sublime.CompletionItem('num','num()'          , 'num()'       ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('get','get()'          , 'get($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('try_get','try_get()'  , 'try_get($0)' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('peek','peek()'        , 'peek($0)'    ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('try_peek','try_peek()', 'try_peek($0)',kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('put','put()'          , 'put($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('try_put','try_put()'  , 'try_put($0)' ,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def semaphore_completion(self):
        c = []
        c.append(sublime.CompletionItem('get','get()'        , 'get($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('try_get','try_get()', 'try_get($0)' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('put','put()'        , 'put($0)'     ,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def process_completion(self):
        c = []
        c.append(sublime.CompletionItem('status','status()'   , 'status()' ,kind=MYKIND_FUNCTION, completion_format=0))
        c.append(sublime.CompletionItem('kill','kill()'       , 'kill()'   ,kind=MYKIND_FUNCTION, completion_format=0))
        c.append(sublime.CompletionItem('resume','resume()'   , 'resume()' ,kind=MYKIND_FUNCTION, completion_format=0))
        c.append(sublime.CompletionItem('await','await()'     , 'await()'  ,kind=MYKIND_FUNCTION, completion_format=0))
        c.append(sublime.CompletionItem('suspend','suspend()' , 'suspend()',kind=MYKIND_FUNCTION, completion_format=0))
        return c

    def enum_completion(self):
        c = []
        c.append(sublime.CompletionItem('first','first()', 'first()',kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('last','last()' , 'last()' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('next','next()' , 'next()' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('prev','prev()' , 'prev()' ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('num','num()'  , 'num()'  ,kind=MYKIND_FUNCTION, completion_format=1))
        c.append(sublime.CompletionItem('name','name()' , 'name()' ,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def cover_completion(self):
        c = [
            sublime.CompletionItem("bins",                 "cover" , "bins"                , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("binsof",               "cover" , "binsof"              , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("coverpoint",           "cover" , "coverpoint"          , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("cross",                "cover" , "cross"               , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("default",              "cover" , "default"             , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("iff",                  "cover" , "iff"                 , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("illegal_bins",         "cover" , "illegal_bins"        , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("ignore_bins",          "cover" , "ignore_bins"         , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("intersect",            "cover" , "intersect"           , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("matches",              "cover" , "matches"             , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("negedge",              "cover" , "negedge"             , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("option",               "cover" , "option"              , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("posedge",              "cover" , "posedge"             , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("type_option",          "cover" , "type_option"         , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("sequence",             "cover" , "sequence"            , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("wildcard",             "cover" , "wildcard"            , kind=MYKIND_KEYWORD),
            sublime.CompletionItem("with_function_sample", "cover" , "with function sample", kind=MYKIND_KEYWORD),
            sublime.CompletionItem("with",                 "cover" , "with"                , kind=MYKIND_KEYWORD)]
        return c

    def constraint_completion(self):
        c = [
            sublime.CompletionItem("solve",   "constraint" ,"solve"       ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("before",  "constraint" ,"before"      ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("soft",    "constraint" ,"soft"        ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("if",      "constraint" ,"if"          ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("else",    "constraint" ,"else"        ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("foreach", "constraint" ,"foreach"     ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("disable", "constraint" ,"disable"     ,kind=MYKIND_KEYWORD),
            sublime.CompletionItem("dist",    "constraint" ,"dist {$0};"  ,kind=sublime.KIND_SNIPPET, completion_format=1),
            sublime.CompletionItem("inside",  "constraint" ,"inside {$0};",kind=sublime.KIND_SNIPPET, completion_format=1),
            sublime.CompletionItem("unique",  "constraint" ,"unique {$0};",kind=sublime.KIND_SNIPPET, completion_format=1)]
        return c

    def get_listbased_info(self,name):
        lname = 'sv.completion.' + name
        l = self.settings.get(lname)
        l_user = self.settings.get(lname+'.user',None)
        if l_user:
            d = { x[0]:i for i,x in enumerate(l)}
            for x in l_user :
                if x[0] in d:
                    l[d[x[0]]] = x
                else :
                    l.append(x)
        # print ([['{0}\t{1}'.format(x[0],x[1]),x[2]] for x in l])
        # print (l)
        return l

    def listbased_completion(self, name):
        l = self.get_listbased_info(name)
        if not l:
            print('[listbased_completion] No completion found for {}'.format(name))
            return []
        k = sublime.KIND_SNIPPET if name in ['tick','core'] else MYKIND_FUNCTION
        c = []
        for x in l:
            exclude = False
            if len(x) > 3:
                for s in x[3]:
                    if s not in self.scope:
                        exclude = True
                        continue
            if exclude:
                continue
            c.append(sublime.CompletionItem(x[0],x[1],x[2],kind=k,completion_format=1) )
        return c

    def struct_completion(self,decl, isAssign=False, fe=[], prev_is_comma=False):
        c = []
        m = re.search(r'\{(.*)\}', decl)
        # print("[struct_completion] decl = {} -> {}".format(decl,m))
        if m is not None:
            fti = verilogutil.get_all_type_info(m.groups()[0])
            # print("[struct_completion] fti = {}".format(fti))
            if isAssign and not fe:
                c.append(sublime.CompletionItem('all_fields','All fields',', '.join(['{0}: ${1}'.format(f['name'],i+1) for i,f in enumerate(fti)]),kind=sublime.KIND_SNIPPET, completion_format=1))
            for f in fti:
                if f['name'] not in fe:
                    f_type = f['type']
                    m = re.search(r'\[.*\]', f['decl'])
                    if m:
                        f_type += m.group(0)
                    f_name = f['name']
                    if prev_is_comma:
                        f_name = ' ' + f_name
                    if isAssign:
                        f_name += ': '
                    c.append(sublime.CompletionItem(f['name'],f_type,f_name,kind=MYKIND_FIELD, completion_format=1))
            if isAssign and 'default' not in fe:
                c.append(sublime.CompletionItem('default','default','default:',kind=MYKIND_KEYWORD))
        # print("[struct_completion] decl = {}".format(decl))
        return c


    def struct_assign_completion(self,view,r,prev_is_comma):
        start_pos = r.a # save original position of caret
        r_start = r.a
        r_end = r.a
        scope = view.scope_name(r.a)
        # Go to the = sign of the assign
        while('meta.struct.assign' in scope):
            r_tmp = view.find_by_class(r_start,False,sublime.CLASS_PUNCTUATION_START)
            scope = view.scope_name(r_tmp)
            # Make sure we do not end into an infinite loop, even though this should never happen due to the check on scope
            if r_start==r_tmp:
                break
            if 'meta.struct.assign' in scope:
                r_start=r_tmp
        # Find end
        scope = view.scope_name(r.a)
        while('meta.struct.assign' in scope):
            r_tmp = view.find_by_class(r_end,True,sublime.CLASS_PUNCTUATION_START)
            scope = view.scope_name(r_tmp)
            # Make sure we do not end into an infinite loop, even though this should never happen due to the check on scope
            if r_end==r_tmp:
                break
            if 'meta.struct.assign' in scope:
                r_end=r_tmp
        if(r_end<start_pos):
            r_end = start_pos
        # Go to the end to get the full scope
        content = view.substr(sublime.Region(r_start,r_end))
        # print('[struct_assign_completion] content = "{0}"'.format(content))

        # get the variable name
        start_line = view.line(sublime.Region(r_start-1,r_start-1)).a
        l = view.substr(sublime.Region(start_line,r_start-1)).strip()
        m = re.search(r'\b(?P<varname>[\w\[\]\.\(\)\+\-\*]+)\s*(<?=)',l)
        if not m:
            return []
        v = m.group('varname')
        ti = verilog_module.type_info_on_hier(view,v,region=sublime.Region(0, start_line))
        # print('[struct_assign_completion] ti = %s' % (ti))
        if not ti['type']:
            return []
        t = ti['type']
        tti = None
        if t in ['struct','enum','logic','bit','reg','wire','input','output','inout']:
            tti = ti
        else :
            t = re.sub(r'\w+\:\:','',t)
            filelist = view.window().lookup_symbol_in_index(t)
            if filelist:
                file_ext = tuple(self.settings.get('sv.sv_ext','sv') + self.settings.get('sv.svh_ext','svh'))
                for f in filelist:
                    fname = sublimeutil.normalize_fname(f[0])
                    if fname.lower().endswith(file_ext):
                        tti = verilog_module.type_info_file(view,fname,t)
                        if tti:
                            # print('[struct_assign_completion] Type %s found in %s: %s' %(ti['type'],fname,str(tti)))
                            break
        # print('[struct_assign_completion] tti = %s' % (tti))
        if not tti:
            return []
        if tti['type'] == 'struct' :
            fe = re.findall(r'(\w+)\s*:',content)
            return self.struct_completion(tti['decl'],True,fe,prev_is_comma)
        elif tti['type'] == 'enum' :
            c = []
            el = verilogutil.get_enum_values(tti['decl'])
            for x in el :
                c.append(sublime.CompletionItem(x,f'Type {t}',x,kind=(sublime.KIND_ID_VARIABLE,'e','Enum'), completion_format=1))
            return c
        else :
            return []

    def class_completion(self, fname,cname, txt=None, publicOnly=True):
        if fname:
            ci = verilogutil.parse_class_file(fname,cname)
        else:
            ci = verilogutil.parse_class(txt,cname)
        # print('[SV:class_completion] Class {0} in file {1} = \n {2}'.format(cname,fname,ci))
        c = []
        if ci:
            #TODO: parse also the extended class (up to a limit ?)
            for x in ci['member']:
                # filter out local and protected variable
                if 'access' not in x:
                    c.append(sublime.CompletionItem(x['name'],x['type'], x['name'],kind=MYKIND_FIELD, completion_format=1))
            for x in ci['function']:
                # filter out local and protected function, and constructor (cannot be called with a .)
                snippet = x['name']+'('
                for i,p in enumerate(x['port']):
                    snippet+= '${{{0}:/*{1}*/}}'.format(i+1,p['decl'])
                    if i != (len(x['port'])-1):
                        snippet+=', '
                snippet+= ')${0}'
                if ('access' not in x or not publicOnly) and x['name'] != 'new':
                    c.append(sublime.CompletionItem(x['name'],x['type'], snippet,kind=MYKIND_FUNCTION, completion_format=1))
        return c

    def module_completion(self, fname, mname):
        mi = verilogutil.parse_module_file(fname, mname)
        c = []
        # Add instances and signals/IO
        # print('[SV:module_completion] mi = {0}'.format(mi))
        for x in mi['inst']:
            c.append(sublime.CompletionItem(x['name'],x['type'], x['name'],kind=MYKIND_FIELD, completion_format=1))
        for x in mi['port']:
            c.append(sublime.CompletionItem(x['name'],x['type'], x['name'],kind=MYKIND_FIELD, completion_format=1))
        for x in mi['signal']:
            c.append(sublime.CompletionItem(x['name'],x['type'], x['name'],kind=MYKIND_FIELD, completion_format=1))
        return c

    # Interface completion: all signal declaration can be used as completion
    def interface_completion(self,fname, iname, modport_only=False):
        ii = verilogutil.parse_module_file(fname, iname)
        # print(ii)
        c = []
        if not modport_only:
            for x in ii['port']:
                c.append(sublime.CompletionItem(x['name'],x['decl'], x['name'],kind=(sublime.KIND_ID_VARIABLE, "p", "I/O"), completion_format=1))
            for x in ii['signal']:
                c.append(sublime.CompletionItem(x['name'],x['decl'], x['name'],kind=(sublime.KIND_ID_VARIABLE, "v", "Field"), completion_format=1))
            if 'clocking' in ii:
                for x in ii['clocking']:
                    c.append(sublime.CompletionItem(x['name'],'Clocking', x['name'],kind=MYKIND_CLOCKING, completion_format=1))
        if 'modport' in ii:
            for x in ii['modport']:
                c.append(sublime.CompletionItem(x['name'],'Modport', x['name'],kind=MYKIND_MODPORT, completion_format=1))
        if not modport_only:
            for x in ii['param']:
                c.append(sublime.CompletionItem(x['name'],'Param', x['name'],kind=(sublime.KIND_ID_VARIABLE, "P", "Param"), completion_format=1))
        return c

    # Provide completion for module binding:
    # Extract all parameter and ports from module definition
    # and filter based on position (parameter or ports) and existing binding
    def module_binding_completion(self,txt_raw,txt,minfo,pos, is_param):
        c = []
        if not minfo:
            return c
        # print(txt_raw)
        # Select parameter or port for completion
        if is_param:
            l = minfo['param']
            m = re.search(r'#\s*\((?P<bind>.*?)\)\s*\w+',txt,flags=re.MULTILINE)
        else:
            l = minfo['port']
            m = re.search(r'\w+\s*\((?P<bind>.*?)\)\s*;',txt,flags=re.MULTILINE)
        if not l:
            return c
        # print('[module_binding_completion] Port/param : ' + str(l))
        # Extract all existing binding
        if m:
            txt = m.group('bind')
        b = re.findall(r'\.(\w+)\b',txt,flags=re.MULTILINE)
        if '\n' in txt:
            len_port = max([len(p['name']) for p in l])
        else:
            len_port = 0
        # Check current line to see if the connection is already done and if we are on the last binding
        eot = verilogutil.clean_comment(txt_raw[pos:])
        has_binding = re.match(r'^\.\w*\b',eot) is not None
        if not has_binding:
            is_last = re.match(r'(?s)^\.\w*\s*(?:\([^\)]+\))?\s*\)\s*(;|\w+)',eot,flags=re.MULTILINE) is not None
        # print('End text = \n{0}\nHas_binding={1}, is_last={2}'.format(eot,has_binding,is_last))
        for x in l:
            if x['name'] not in b:
                if is_param:
                    tips = str(x['value'])
                    def_val = str(x['value'])
                else:
                    tips = str(x['type'])
                    def_val = x['name']
                s = x['name']
                if not has_binding:
                    s = s.ljust(len_port)+'(${0:' + def_val + '})'
                    if not is_last:
                        s = s+','
                c.append(sublime.CompletionItem(x['name'],tips,s,kind=MYKIND_FIELD, completion_format=1))
        return c

    # Complete case for an enum with all possible value
    def case_completion(self,sig):
        c = []
        (s,el) = VerilogHelper.get_case_template(self.view, sig)
        if s:
            c.append(sublime.CompletionItem('case','case Template',s,kind=sublime.KIND_SNIPPET, completion_format=1))
        return c

    # Complete enum assign/comparison with all possible value
    def enum_assign_completion(self, view, sname):
        c = []
        r = sublime.Region(0, view.size())
        if '.' in sname :
            ti = verilog_module.type_info_on_hier(view,sname,region=r)
        else :
            ti = verilog_module.type_info(view,view.substr(r),sname)
        # print(f'[enum_assign_completion] {sname}: {ti}')
        if ti and ti['type']:
            typename = ti['type']
            if ti['type'] not in ['enum','logic','bit','reg','wire','input','output','inout','struct']:
                ti = verilog_module.lookup_type(view,ti['type'])
                # print(f'[enum_assign_completion] : {typename} expands to {ti}')
            if ti and ti['type']=='enum':
                el = verilogutil.get_enum_values(ti['decl'])
                for x in el :
                    c.append(sublime.CompletionItem(x,f'Type {typename}',x,kind=(sublime.KIND_ID_VARIABLE,'e','Enum'), completion_format=1))
        return c

    # Completion for ::
    def scope_completion(self,view,w):
        c = []
        # get type : expect a package, an enum or a class (not supported yet)
        ti = verilog_module.lookup_type(view,w)
        if not ti:
            return c
        # print(ti)
        # In case of enum, provide all possible value
        if ti['type'] == 'enum' :
            m = re.search(r'\{(.*)\}', ti['decl'])
            if m :
                el = re.findall(r"(\w+).*?(,|$)",m.groups()[0])
                c = [[x[0],x[0]] for x in el]
        elif ti['type'] == 'package':
            with open(ti['fname'][0], 'r') as f:
                flines = str(f.read())
            ti = verilogutil.parse_package(flines)
            if ti:
                for x in ti:
                    s = x['name']
                    if x['type'] in ['function','task']:
                        s = self.function_snippet(x)
                    c.append(sublime.CompletionItem(x['name'],x['type'],s,kind=MYKIND_FIELD, completion_format=1))
        elif ti['type'] == 'class':
            sublime.status_message('Autocompletion for class scope unsupported for the moment')
        return c

    def function_snippet(self,fi):
        s = fi['name'] + '('
        for i,p in enumerate(fi['port']):
            s+= '${{{0}:/*{1}*/}}'.format(i+1,p['decl'])
            if i != (len(fi['port'])-1):
                s+=', '
        s+= ')${0}'
        return s

    # Completion for endfunction, endtask, endclass, endmodule, endpackage, endinterface with label
    def end_completion(self,view,r,prefix):
        re_str = None
        kw = ''
        if prefix == 'end':
            # Extract line to get indentation. Start region one character to the righft to be sure we do not take previous line
            l = self.view.substr(view.line(sublime.Region(r.a+1,r.b)))
            m = re.match(r'(\s*)',l)
            re_str = r'^' + m.groups()[0] + r'((\w+.*)?(begin)\s*(:\s*(\w+))?|(?:virtual\s+)?(function)\s+(?:(?:automatic|static)\s+)?(?:\w+\s+)?(?:\w+\:\:)?(\w+)\s*\(|(class)\s+(\w+)|(module)\s+(\w+)|(package)\s+(?:(?:automatic|static)\s+)?(\w+)|(interface)\s+(\w+)|(?:virtual\s+)?(task)\s+(?:\w+\:\:)?(\w+)|(case)\s*\((.+)\)|(generate)|(covergroup)\s+(\w+))'
        elif prefix.startswith('endf'):
            re_str = r'function\s+(?:(?:automatic|static)\s+)?(?:\w+\s+)?(?:\w+\:\:)?(\w+)\s*\('
            kw = 'endfunction'
        elif prefix.startswith('endt'):
            re_str = r'task\s+(?:\w+\:\:)?(\w+)'
            kw = 'endtask'
        elif prefix.startswith('endc'):
            if prefix == 'endc' :
                l = self.view.substr(view.line(sublime.Region(r.a+1,r.b)))
                m = re.match(r'(\s*)',l)
                re_str = r'^' + m.groups()[0] + r'((class)\s+(\w+)|(case)\s*\((.+)\))'
                kw = 'endc?'
            elif prefix.startswith('endcl'):
                re_str = r'class\s+(\w+)'
                kw = 'endclass'
            elif prefix.startswith('endca'):
                re_str = r'case\s*\((.+)\)'
                kw = 'endcase'
        elif prefix.startswith('endm'):
            re_str = r'module\s+(\w+)'
            kw = 'endmodule'
        elif prefix.startswith('endp'):
            re_str = r'package\s+(?:(?:automatic|static)\s+)?(\w+)'
            kw = 'endpackage'
        elif prefix.startswith('endi'):
            re_str = r'interface\s+(\w+)'
            kw = 'endinterface'
        elif prefix.startswith('endg'):
            if prefix == 'endg':
                l = self.view.substr(view.line(sublime.Region(r.a+1,r.b)))
                m = re.match(r'(\s*)',l)
                re_str = r'^' + m.groups()[0] + r'((generate)|(covergroup)\s+(\w+))'
                kw = 'endg?'
            elif prefix.startswith('endge'):
                re_str = r'\bgenerate\b()?'
                kw = 'endgenerate'
            elif prefix.startswith('endgr'):
                re_str = r'\bcovergroup\s+(\w+)?'
                kw = 'endgroup'
        # Unknown prefix => quit
        if not re_str:
            return []
        # find closest block start
        nl = []
        ra = view.find_all(re_str,0,'$1',nl)
        name = ''
        if ra:
            # print(nl)
            for (rf,n) in zip(ra,nl):
                if rf.a < r.a:
                    name = n
                else:
                    break
        # Process keyword if not properly defined yet
        sep  = '//' if self.settings.get("sv.end_label_comment") else ':'
        if kw == 'endc?' :
            m = re.match(re_str[1:].strip(),name,flags=re.MULTILINE)
            if m:
                # print(m.groups())
                if m.groups()[1] == 'class':
                    kw = 'endclass'
                    name = m.groups()[2]
                elif m.groups()[3] == 'case':
                    kw = 'endcase'
                    name = m.groups()[4]
        if kw == 'endg?' :
            m = re.match(re_str[1:].strip(),name,flags=re.MULTILINE)
            if m:
                # print(m.groups())
                if m.groups()[1] == 'generate':
                    kw = 'endgenerate'
                    name = ''
                elif m.groups()[2] == 'covergroup':
                    kw = 'endgroup'
                    name = m.groups()[3]
        elif not kw:
            m = re.match(re_str[1:].strip(),name,flags=re.MULTILINE)
            if m:
                # print(m.groups())
                if m.groups()[2] == 'begin':
                    kw = 'end'
                    name = m.groups()[4]
                    if not name:
                        sep = '//'
                        name = m.groups()[1]
                elif m.groups()[5] == 'function':
                    kw = 'endfunction'
                    name = m.groups()[6]
                elif m.groups()[7] == 'class':
                    kw = 'endclass'
                    name = m.groups()[8]
                elif m.groups()[9] == 'module':
                    kw = 'endmodule'
                    name = m.groups()[10]
                elif m.groups()[11] == 'package':
                    kw = 'endpackage'
                    name = m.groups()[12]
                elif m.groups()[13] == 'interface':
                    kw = 'endinterface'
                    name = m.groups()[14]
                elif m.groups()[15] == 'task':
                    kw = 'endtask'
                    name = m.groups()[16]
                elif m.groups()[17] == 'case':
                    kw = 'endcase'
                    name = m.groups()[18]
                elif m.groups()[19] == 'generate':
                    kw = 'endgenerate'
                    name = ''
                elif m.groups()[20] == 'covergroup':
                    kw = 'endgroup'
                    name = m.groups()[21]
        # Provide completion with optional label
        if name:
            c_str = f'{kw} {sep} {name.strip()}'
        else:
            c_str = kw
        return [[kw+'\t'+c_str,c_str]]


##############################################
#
class VerilogHelper():

    def get_always_template(view):
        settings = view.settings()
        clk_name          = settings.get('sv.clk_name','clk')
        rst_name          = settings.get('sv.rst_name','rst')
        rst_n_name        = settings.get('sv.rst_n_name','rst_n')
        clk_en_name       = settings.get('sv.clk_en_name','clk_en')
        always_name_auto  = settings.get('sv.always_name_auto',True)
        always_ce_auto    = settings.get('sv.always_ce_auto',True)
        always_label      = settings.get('sv.always_label',True)
        always_begin_end  = settings.get('sv.always_ff_begin_end',True)
        always_one_cursor = settings.get('sv.always_one_cursor',True)
        indent_style      = settings.get('sv.indent_style','1tbs')
        beautifier = verilog_beautifier.VerilogBeautifier(useTab=True, indentSyle=indent_style)
        txt = ''
        # try to retrieve name of clk/reset base on buffer content (if enabled in settings)
        if always_name_auto :
            pl = [] # posedge list
            r = view.find_all(r'posedge\s+(\w+)', 0, '$1', pl)
            mi = None
            if pl:
                # Make hypothesis that all clock signals have a c in their name
                pl_c = [x for x in pl if 'c' in x.lower()]
                # select most common one only if the name defined in settings is not in the list
                if clk_name not in set(pl):
                    if pl_c :
                        clk_name = collections.Counter(pl_c).most_common(1)[0][0]
                if rst_name not in set(pl):
                    # Make hypothesis that the reset high signal does not have a 'c' in the name (and that's why active low reset is better :P)
                    pl_r = [x for x in pl if x not in pl_c]
                    if pl_r:
                        rst_name = collections.Counter(pl_r).most_common(1)[0][0]
            # No posedge found ? try to find a signal name that sounds like a clock
            else:
                txt = view.substr(sublime.Region(0, view.size()))
                txt = verilogutil.clean_comment(txt)
                # Find a port/signal 1b declaration starting with a clock like name (clk,ck,clock)
                sig = re.findall(r'(?i)(?:input|output|var|logic|wire|reg)\s+(?:\w+\s*,\s*)*((?:[cC][lL][kK]|[cC][kK]|[cC][lL][oO][cC][kK])(?:\w+)?)\s*(?:,|;|\))',txt)
                # select first one
                if sig:
                    clk_name = sig[0]

            # Try to find the reset active low signal name
            #  - Select most common signal in the negedge list
            #  - If none check port and input for reset like name
            nl = []
            r = view.find_all(r'negedge\s+(\w+)', 0, '$1', nl)
            if nl:
                if rst_n_name not in set(pl):
                    rst_n_name = collections.Counter(nl).most_common(1)[0][0]
            else :
                if not txt:
                    txt = view.substr(sublime.Region(0, view.size()))
                    txt = verilogutil.clean_comment(txt)
                # Find a port/signal 1b declaration starting with a reset like name (rst,reset)
                sig = re.findall(r'(?i)(?:input|output|var|logic|wire|reg)\s+(?:\w+\s*,\s*)*((?:[rR][eE]?[sS][eE]?[tT])(?:\w+)?)\s*(?:,|;|\))',txt)
                # select first one
                if sig:
                    rst_n_name = sig[0]

        if always_ce_auto and clk_en_name != '':
            r = view.find(verilogutil.re_decl+clk_en_name,0)
            if not r :
                clk_en_name = ''
        # define basic always block with asynchronous reset
        a_l = 'always @(posedge '+clk_name+' or negedge ' + rst_n_name +')'
        if always_begin_end:
            a_l +=  ' begin'
            if always_label :
                a_l +=  ' : proc_$1'
        a_l +=  '\n'
        a_l += 'if(~'+rst_n_name + ') begin\n'
        a_l += '$1 <= 0;'
        a_l += '\nend else '
        if clk_en_name != '':
            a_l += 'if(' + clk_en_name + ') '
        a_l+= 'begin\n'
        if not always_one_cursor:
            a_l += '$1 <= $2;'
        a_l+= '\nend\n'
        if always_begin_end:
            a_l+= 'end'
        # define basic always block with no reset
        a_nr = 'always @(posedge '+clk_name +')'
        if always_begin_end or clk_en_name=='':
            a_nr +=  ' begin'
            if always_label :
                a_nr +=  ' : proc_$1'
        a_nr +=  '\n'
        if clk_en_name != '':
            a_nr += 'if(' + clk_en_name + ') begin\n'
        a_nr += '$1'
        if not always_one_cursor:
            a_nr += ' <= $2'
        a_nr+= ';\nend\n'
        if always_begin_end and clk_en_name:
            a_nr+= 'end'
        a_l = beautifier.beautifyText(a_l)
        # define basic always block with asynchronous reset active high
        a_h = a_l.replace('neg','pos').replace(rst_n_name,rst_name).replace('~','')
        a_nr = beautifier.beautifyText(a_nr).replace('$1;','$1') #the ; was just here for proper indentation
        return (a_l[7:],a_h[7:],a_nr[7:])

    def get_case_template(view, sig_name, ti=None):
        debug = view.settings().get("sv.debug",False)
        m = re.search(r'(?P<name>[\w\.]+)(\s*\[(?P<h>\d+)\:(?P<l>\d+)\])?',sig_name)
        if not m:
            print('[SV:get_case_template] Could not parse ' + sig_name)
            return (None,None)
        if not ti:
            ti = verilog_module.type_info_on_hier(view,m.group('name'),view.substr(sublime.Region(0, view.size())))
        if not ti['type']:
            print('[SV:get_case_template] Could not retrieve type of ' + m.group('name'))
            return (None,None)
        length = 0
        if m.group('h'):
            length = int(m.group('h')) - int(m.group('l')) + 1
        t = ti['type'].split()[0]
        if debug:
            print('[get_case_template] ti = {0}'.format(ti))
        if t not in ['enum','logic','bit','reg','wire','input','output','inout']:
            #check first in current file
            tti = verilog_module.type_info(view,view.substr(sublime.Region(0, view.size())),ti['type'])
            # Not in current file ? look in index
            if not tti['type']:
                filelist = view.window().lookup_symbol_in_index(ti['type'])
                if filelist:
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        tti = verilog_module.type_info_file(view,fname,t)
                        if tti:
                            break
            if debug:
                print('[get_case_template] tti = {0}'.format(tti))
            ti = tti
        return verilogutil.fill_case(ti,length)

##############################################
#
class VerilogInsertFsmTemplate(sublime_plugin.TextCommand):

    #TODO: use parse module function instead of doing search again. We are missing case of input
    # Might want to add some type info in the show quick panel
    def run(self,edit):
        #List all signals available and let user choose one
        mi = verilogutil.parse_module(self.view.substr(sublime.Region(0,self.view.size())),r'\w+')
        # print(mi)
        self.til = [x for x in mi['port']]
        self.til = [x for x in mi['signal'] if not x['decl'].startswith('typedef')]
        self.dl =[[x['name'],x['type']+' '+x['bw']] for x in self.til]
        sublime.active_window().show_quick_panel(self.dl, self.on_done )
        return

    def on_done(self, index):
        if index >= 0:
            self.view.run_command("verilog_do_insert_fsm_template", {"args":{'ti':self.til[index]}})


class VerilogDoInsertFsmTemplate(sublime_plugin.TextCommand):

    def run(self,edit, args):
        # print('ti = ' + str(args['ti']))
        sig_name = args['ti']['name']
        # Retrieve complete type information of signal
        (s,el) = VerilogHelper.get_case_template(self.view, sig_name,args['ti'])
        if not s:
            return
        state_next = sig_name + '_next'
        s = s.replace('\n','\n\t') # insert an indentation level
        s = 'case (' + sig_name+')'+s
        s = 'always_comb begin : proc_' + state_next + '\n\t' + state_next + ' = ' + sig_name +';\n\t' + s + '\nend'
        (a_l,a_h,a_nr) = VerilogHelper.get_always_template(self.view)
        fname = self.view.file_name()
        if fname:
            is_sv = fname.lower().endswith(tuple(self.view.settings().get('sv.sv_ext','sv')))
        else:
            is_sv = False
        if is_sv:
            a_l = 'always_ff ' + a_l
        else :
            a_l = 'always' + a_l
        a_l = a_l.replace('$1',sig_name)
        a_l = a_l.replace('<= 0','<= ' + str(el[0]))
        a_l = a_l.replace('$2',state_next)
        s = a_l + '\n\n' + s
        proc_indent = self.view.settings().get('sv.proc_indent',1)
        if proc_indent>0:
            s = proc_indent*'\t' + s.replace('\n','\n'+proc_indent*'\t')
        self.view.insert(edit,self.view.sel()[0].a,s)
        # Check is state_next exist: if not, add it to the declaration next to state
        ti = verilog_module.type_info(self.view,self.view.substr(sublime.Region(0, self.view.size())),state_next)
        if not ti['type']:
            r = self.view.find(args['ti']['type']+r'.+'+sig_name,0)
            self.view.replace(edit,r,re.sub(r'\b'+sig_name+r'\b',sig_name+', '+state_next,self.view.substr(r)))
