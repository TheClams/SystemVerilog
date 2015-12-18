import sublime, sublime_plugin
import re, string, os, sys, imp
import collections

try:
    from SystemVerilog.verilogutil import verilogutil
    from SystemVerilog.verilogutil import verilog_beautifier
    from SystemVerilog.verilogutil import sublimeutil
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
    import verilogutil
    import verilog_beautifier
    import sublimeutil

try:
    from SystemVerilog import verilog_module
    import verilog_module
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    import verilog_module

############################################################################

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(verilog_beautifier)
    imp.reload(sublimeutil)
    imp.reload(verilog_module)

class VerilogAutoComplete(sublime_plugin.EventListener):

    # Cache latest information
    cache_module = {'name' : '', 'date' : 0, 'info' : None}

    def on_query_completions(self, view, prefix, locations):
        # don't change completion if we are not in a systemVerilog file
        if not view.match_selector(locations[0], 'source.systemverilog'):
            return []
        self.view = view
        self.settings = view.settings()
        if self.settings.get("sv.disable_autocomplete"):
            return []
        r = view.sel()[0]
        scope = view.scope_name(r.a)
        # If there is a prefix, allow sublime to provide completion ?
        flag = 0
        if(prefix==''):
            flag = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
        # Get previous character
        r.a = r.a - 1 - len(prefix)
        r.b = r.a+1
        t = view.substr(r)
        completion = []
        # print('[SV:on_query_completions] prefix="%s" previous char="%s"' %(prefix,t))
        # Select completion function
        if t=='$':
            completion = self.systemtask_completion()
        elif t=='`':
            completion =  self.tick_completion()
        elif t=='.':
            completion =  self.dot_completion(view,r)
        elif t==':':
            completion =  self.scope_completion(view,r)
        elif t==')':
            l = view.substr(view.line(r))
            m = re.search(r'^\s*case\s*\((.+?)\)',l)
            if m:
                completion = self.case_completion(m.groups()[0])
        elif 'meta.struct.assign' in scope:
            completion = self.struct_assign_completion(view,r)
        elif prefix:
            # Provide completion for most used uvm function
            if(prefix.startswith('u')):
                completion = self.uvm_completion()
            # Provide completion for most always block
            elif(prefix.startswith('a')):
                completion = self.always_completion()
            # Provide completion for modport
            elif(prefix.startswith('m')):
                completion = self.modport_completion()
            # Provide completion for endfunction, endtask, endclass, endmodule, endpackage, endinterface
            elif(prefix.startswith('end')):
                completion = self.end_completion(view,r,prefix)
        return (completion, flag)

    def uvm_completion(self):
        c = []
        c.append(['uvm_config_db_get' , 'uvm_config_db#()::get(this, "$1", "$0", $0);' ])
        c.append(['uvm_config_db_set' , 'uvm_config_db#()::set(this, "$1", "$0", $0);' ])
        c.append(['uvm_report_info'   , 'uvm_report_info("$1", "$0", UVM_NONE);' ])
        c.append(['uvm_report_warning', 'uvm_report_warning("$1", "$0");' ])
        c.append(['uvm_report_error'  , 'uvm_report_error("$1", "$0");' ])
        c.append(['uvm_report_fatal'  , 'uvm_report_fatal("$1", "$0");' ])
        return c

    def always_completion(self):
        c = []
        (a_l,a_h,a_nr) = VerilogHelper.get_always_template(self.view)
        #Provide completion specific to the file type
        fname = self.view.file_name()
        if fname:
            is_sv = os.path.splitext(fname)[1].startswith('.sv')
        else:
            is_sv = False
        if is_sv :
            c.append(['always_ff\talways_ff Async','always_ff '+a_l])
            c.append(['always_ffh\talways_ff Async high','always_ff '+a_h])
            c.append(['always_c\talways_comb','always_comb begin : proc_$0\n\nend'])
            c.append(['always_l\talways_latch','always_latch begin : proc_$0\n\nend'])
            c.append(['always_ff_nr\talways_ff No reset','always_ff '+a_nr])
            c.append(['always_ffs\talways_ff Sync','always_ff '+re.sub(r' or negedge \w+','',a_l)])
            c.append(['always_ffsh\talways_ff Sync high','always_ff '+re.sub(r' or posedge \w+','',a_h)])
        if not is_sv or not self.settings.get('sv.always_sv_only') :
            c.append(['always\talways Async','always '+a_l])
            c.append(['alwaysh\talways Async high','always '+a_h])
            c.append(['alwaysc\talways *','always @(*) begin : proc_$0\n\nend'])
            c.append(['always_nr\talways NoReset','always_ff '+a_nr])
            c.append(['alwayss\talways sync','always '+re.sub(r' or negedge \w+','',a_l)])
            c.append(['alwayssh\talways sync high','always '+re.sub(r' or posedge \w+','',a_h)])
        return c

    def modport_completion(self):
        c = []
        txt = self.view.substr(sublime.Region(0,self.view.size()))
        ti = verilogutil.parse_module(txt,r'\w+')
        if not ti:
            return c
        modport = 'modport $0 ('
        for i,s in enumerate(ti['signal']):
            modport += s['name']
            if i!= len(ti['signal'])-1:
                modport += ', '
        modport += ');'
        return [['modport\tModport template',modport]]


    def dot_completion(self,view,r):
        # select word before the dot and quit with no completion if no word found
        start_pos = r.a # save original position of the .
        start_word = view.substr(view.word(r))
        r.a -=1
        r.b = r.a
        r = view.word(r);
        w = str.rstrip(view.substr(r))
        scope = view.scope_name(r.a)
        completion = []
        # print ('previous word: ' + w)
        if w=='' or not re.match(r'\w+',w) or start_word.startswith('('):
            #No word before dot => check the scope
            if 'meta.module.inst' in scope:
                r = sublimeutil.expand_to_scope(view,'meta.module.inst',r)
                txt = view.substr(r)
                mname = re.findall(r'\w+',txt)[0]
                filelist = view.window().lookup_symbol_in_index(mname)
                if filelist:
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        mi = verilogutil.parse_module_file(fname,mname)
                        if mi:
                            break
                    is_param = 'meta.module-param' in scope
                    completion = self.module_binding_completion(txt, mi,start_pos-r.a,is_param)
            else :
                return completion
        else :
            modport_only = False
            # Check for multiple level of hierarchy
            cnt = 1
            autocomplete_max_lvl = self.settings.get("sv.autocomplete_max_lvl",4)
            while r.a>1 and self.view.substr(sublime.Region(r.a-1,r.a))=='.' and (cnt < autocomplete_max_lvl or autocomplete_max_lvl<0):
                if 'support.function.port' not in self.view.scope_name(r.a):
                    r.a = self.view.find_by_class(r.a-3,False,sublime.CLASS_WORD_START)
                cnt += 1
            if (cnt >= autocomplete_max_lvl and autocomplete_max_lvl>=0):
                print("[SV:dot_completion] Reached max hierarchy level for autocompletion. You can change setting sv.autocomplete_max_lvl")
                return completion
            w = str.rstrip(view.substr(r))
            # get type information on the variable
            txt = view.substr(sublime.Region(0, view.size()))
            wa = w.split('.')
            # extract info for first word using current file (to allow unsaved change to be taken into account)
            ti = verilogutil.get_type_info(txt,wa[0])
            for i in range(1,len(wa)):
                # print("[SV:dot_completion] Type of {0} = {1}".format(wa[i-1],ti))
                if not ti or not ti['type']:
                    print("[SV:dot_completion] Cound not find type of {0} in {1}".format(wa[i-1],wa))
                    return completion
                if ti['type']=='module':
                    ti = verilog_module.lookup_module(self.view,ti['name'])
                else:
                    ti = verilog_module.lookup_type(self.view,ti['type'])
                # Lookup for the variable inside the type defined
                if ti:
                    fname = ti['fname'][0]
                    ti = verilogutil.get_type_info_file(fname,wa[i])
            # print ('Type info: ' + str(ti))
            if not ti or (ti['type'] is None and 'meta.module.systemverilog' not in scope):
                return completion
            #Provide completion for different type
            if ti['array']!='' :
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
                completion = ['triggered','triggered']
            # Non standard type => try to find the type in the lookup list and get the type
            else:
                # Force the type to the word itself if we are in a module declaration : typical of modport
                if ti['type'] is None and 'meta.module.systemverilog' in scope:
                    t = w
                    modport_only = True
                elif ti['type']=='module':
                    t = w
                else:
                    t = ti['type']
                t = re.sub(r'\w+\:\:','',t) # remove scope from type. TODO: use the scope instead of rely on global lookup
                filelist = view.window().lookup_symbol_in_index(t)
                # print(' Filelist for ' + t + ' = ' + str(filelist))
                if filelist:
                    tti = None
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        # Parse only verilog files. Check might be a bit too restrictive ...
                        if fname.lower().endswith(('sv','svh', 'v', 'vh')):
                            # print(w + ' of type ' + t + ' defined in ' + str(fname))
                            tti = verilogutil.get_type_info_file(fname,t)
                            if tti['type']:
                                break
                    # print(tti)
                    if not tti:
                        return completion
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
                    completion.append(['randomize\trandomize()','randomize()'])
        return completion

    def array_completion(self,array_type):
        c = []
        if array_type == 'queue':
            c.append(['size\tsize()'            ,'size()'      ])
            c.append(['insert\tinsert()'        ,'insert()'    ])
            c.append(['delete\tdelete()'        ,'delete()'    ])
            c.append(['pop_front\tpop_front()'  ,'pop_front()' ])
            c.append(['pop_back\tpop_back()'    ,'pop_back()'  ])
            c.append(['push_front\tpush_front()','push_front()'])
            c.append(['push_back\tpush_back()'  ,'push_back()' ])
        elif array_type == 'associative':
            c.append(['num\tnum()'      ,'num()'   ])
            c.append(['size\tsize()'    ,'size()'  ])
            c.append(['delete\tdelete()','delete()'])
            c.append(['exists\texists()','exists()'])
            c.append(['first\tfirst()'  ,'first()' ])
            c.append(['last\tlast()'    ,'last()'  ])
            c.append(['next\tnext()'    ,'next()'  ])
            c.append(['prev\tprev()'    ,'prev()'  ])
        else : # Fixed or dynamic have the same completion
           c.append(['size\tsize()'                 ,'size()'                  ])
           c.append(['find\tfind() ...'             ,'find(x) with(x$1)'       ])
           c.append(['find_index\tfind_index() ...' ,'find_index(x) with (x$1)'])
           c.append(['find_first\tfind_first() ...' ,'find_first(x) with (x$1)'])
           c.append(['find_last\tfind_last()'       ,'find_last(x) with (x$1)' ])
           c.append(['unique\tunique()'             ,'unique()'                ])
           c.append(['uniques\tuniques() ...'       ,'uniques(x) with(x$1)'    ])
           c.append(['reverse\treverse()'           ,'reverse()'               ])
           c.append(['sort\tsort()'                 ,'sort()'                  ])
           c.append(['rsort\trsort()'               ,'rsort()'                 ])
           c.append(['shuffle\tshuffle()'           ,'shuffle()'               ])
        # Method available to all types of array
        c.append(['min\tmin()'        ,'min()'    ])
        c.append(['max\tmax()'        ,'max()'    ])
        c.append(['sum\tsum()'        ,'sum()'    ])
        c.append(['product\tproduct()','product()'])
        c.append(['and\tand()'        ,'and()'    ])
        c.append(['or\tor()'          ,'or()'     ])
        c.append(['xor\txor()'        ,'xor()'    ])
        return c

    def string_completion(self):
        c = []
        c.append(['len\tlen()'          , 'len($0)'     ])
        c.append(['substr\tsubstr()'    , 'substr($0)'  ])
        c.append(['putc\tputc()'        , 'putc($0)'    ])
        c.append(['getc\tgetc()'        , 'getc($0)'    ])
        c.append(['toupper\ttoupper()'  , 'toupper($0)' ])
        c.append(['tolower\ttolower()'  , 'tolower($0)' ])
        c.append(['compare\tcompare()'  , 'compare($0)' ])
        c.append(['icompare\ticompare()', 'icompare($0)'])
        c.append(['atoi\tatoi()'        , 'atoi($0)'    ])
        c.append(['atohex\tatohex()'    , 'atohex($0)'  ])
        c.append(['atobin\tatobin()'    , 'atobin($0)'  ])
        c.append(['atoreal\tatoreal()'  , 'atoreal($0)' ])
        c.append(['itoa\titoa()'        , 'itoa($0)'    ])
        c.append(['hextoa\thextoa()'    , 'hextoa($0)'  ])
        c.append(['octoa\toctoa()'      , 'octoa($0)'   ])
        c.append(['bintoa\tbintoa()'    , 'bintoa($0)'  ])
        c.append(['realtoa\trealtoa()'  , 'realtoa($0)' ])
        return c

    def mailbox_completion(self):
        c = []
        c.append(['num\tnum()'          , 'num($0)'     ])
        c.append(['get\tget()'          , 'get($0)'     ])
        c.append(['try_get\ttry_get()'  , 'try_get($0)' ])
        c.append(['peek\tpeek()'        , 'peek($0)'    ])
        c.append(['try_peek\ttry_peek()', 'try_peek($0)'])
        c.append(['put\tput()'          , 'put($0)'     ])
        c.append(['try_put\ttry_put()'  , 'try_put($0)' ])
        return c

    def semaphore_completion(self):
        c = []
        c.append(['get\tget()'        , 'get($0)'     ])
        c.append(['try_get\ttry_get()', 'try_get($0)' ])
        c.append(['put\tput()'        , 'put($0)'     ])
        return c

    def process_completion(self):
        c = []
        c.append(['status\tstatus()'   , 'status($0)' ])
        c.append(['kill\tkill()'       , 'kill($0)'   ])
        c.append(['resume\tresume()'   , 'resume($0)' ])
        c.append(['await\tawait()'     , 'await($0)'  ])
        c.append(['suspend\tsuspend()' , 'suspend($0)'])
        return c

    def systemtask_completion(self):
        c = []
        c.append(['display\t$display()'              , 'display("$0",);'         ])
        c.append(['sformatf\t$sformatf()'            , 'sformatf("$0",)'         ])
        c.append(['test$plusargs\t$test$plusargs()'  , 'test\$plusargs("$0")'    ])
        c.append(['value$plusargs\t$value$plusargs()', 'value\$plusargs("$1",$2)'])
        c.append(['finish\t$finish'                  , 'finish;'                 ])
        #variable
        c.append(['time\t$time'                      , 'time()'                  ])
        c.append(['realtime\t$realtime()'            , 'realtime()'              ])
        c.append(['random\t$random()'                , 'random()'                ])
        c.append(['urandom_range\t$urandom_range()'  , 'urandom_range($1,$2)'    ])
        #cast
        c.append(['cast\t$cast()'                    , 'cast($0)'                ])
        c.append(['unsigned\t$unsigned()'            , 'unsigned($0)'            ])
        c.append(['signed\t$signed()'                , 'signed($0)'              ])
        c.append(['itor\t$itor()'                    , 'itor($0)'                ])
        c.append(['rtoi\t$rtoi()'                    , 'rtoi($0)'                ])
        c.append(['bitstoreal\t$bitstoreal()'        , 'bitstoreal($0)'          ])
        c.append(['realtobits\t$realtobits()'        , 'realtobits($0)'          ])
        #assertion
        c.append(['assertoff\t$assertoff()'          , 'assertoff($0,)'          ])
        c.append(['info\t$info()'                    , 'info("$0");'             ])
        c.append(['error\t$error()'                  , 'error("$0");'            ])
        c.append(['warning\t$warning()'              , 'warning("$0");'          ])
        c.append(['stable\t$stable()'                , 'stable($0)'              ])
        c.append(['fell\t$fell()'                    , 'fell($0)'                ])
        c.append(['rose\t$rose()'                    , 'rose($0)'                ])
        c.append(['past\t$past()'                    , 'past($0)'                ])
        c.append(['isunknown\t$isunknown()'          , 'isunknown($0)'           ])
        c.append(['onehot\t$onehot()'                , 'onehot($0)'              ])
        c.append(['onehot0\t$onehot0()'              , 'onehot0($0)'             ])
        #utility
        c.append(['size\t$size()'                    , 'size($0)'                ])
        c.append(['clog2\t$clog2()'                  , 'clog2($0)'               ])
        c.append(['countones\t$countones()'          , 'countones($0)'           ])
        c.append(['high\t$high()'                    , 'high($0)'                ])
        c.append(['low\t$low()'                      , 'low($0)'                 ])
        #file
        c.append(['fopen\t$fopen()'                  , 'fopen($0,"r")'           ])
        c.append(['fclose\t$fclose()'                , 'fclose($0);'             ])
        c.append(['fflush\t$fflush()'                , 'fflush;'                 ])
        c.append(['fgetc\t$fgetc()'                  , 'fgetc($0,)'              ])
        c.append(['fgets\t$fgets()'                  , 'fgets($0,)'              ])
        c.append(['fwrite\t$fwrite()'                , 'fwrite($0,"")'           ])
        c.append(['readmemb\t$readmemb()'            , 'readmemb("$1",$2)'       ])
        c.append(['readmemh\t$readmemh()'            , 'readmemh("$1",$2)'       ])
        c.append(['sscanf\t$sscanf()'                , 'sscanf($1,"$2",$3)'      ])
        return c

    def tick_completion(self):
        c = []
        c.append(['include\t`include ...'         , 'include "$0"'                ])
        c.append(['define\t`define ...'           , 'define $0'                   ])
        c.append(['ifdef\t`ifdef ...'             , 'ifdef $0'                    ])
        c.append(['ifndef\t`ifndef ...'           , 'ifndef $0'                   ])
        c.append(['else\t`else '                  , 'else '                       ])
        c.append(['elsif\t`elsif ...'             , 'elsif $0'                    ])
        c.append(['endif\t`endif'                 , 'endif'                       ])
        c.append(['celldefine\t`celldefine ...'   , 'celldefine $0 endcelldefine' ])
        c.append(['endcelldefine\t`endcelldefine ', 'endcelldefine '              ])
        c.append(['line\t`line '                  , 'line '                       ])
        c.append(['resetall\t`resetall '          , 'resetall'                    ])
        c.append(['timescale\t`timescale ...'     , 'timescale $0'                ])
        c.append(['undef\t`undef ...'             , 'undef $0'                    ])
        return c

    def enum_completion(self):
        c = []
        c.append(['first\tfirst()', 'first()'])
        c.append(['last\tlast()' , 'last()' ])
        c.append(['next\tnext()' , 'next()' ])
        c.append(['prev\tprev()' , 'prev()' ])
        c.append(['num\tnum()'  , 'num()'  ])
        c.append(['name\tname()' , 'name()' ])
        return c

    def struct_completion(self,decl, isAssign=False, fe=[]):
        c = []
        m = re.search(r'\{(.*)\}', decl)
        if m is not None:
            fti = verilogutil.get_all_type_info(m.groups()[0])
            if isAssign and not fe:
                c.append(['all_fields\tAll fields',', '.join([f['name']+':' for f in fti])])
            for f in fti:
                if f['name'] not in fe:
                    f_type = f['type']
                    m = re.search(r'\[.*\]', f['decl'])
                    if m:
                        f_type += m.group(0)
                    f_name = f['name']
                    if isAssign:
                        f_name += ':'
                    c.append([f['name']+'\t'+f_type,f_name])

        return c

    def struct_assign_completion(self,view,r):
        start_pos = r.a # save original position of the .
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
        # print('[struct_assign_completion] content = %s' % (content))
        if not content.startswith('='):
            # print('[struct_assign_completion] Unexpected char at start of struct assign : ' + content)
            return []
        # get the variable name
        v = view.substr(view.word(sublime.Region(r_start-1,r_start-1)))
        txt = self.view.substr(sublime.Region(0, r_start))
        ti = verilogutil.get_type_info(txt,v)
        # print('[struct_assign_completion] ti = %s' % (ti))
        if not ti['type']:
            return []
        t = ti['type']
        if t == 'struct':
            tti = ti
        else :
            t = re.sub(r'\w+\:\:','',t)
            filelist = view.window().lookup_symbol_in_index(t)
            tti = None
            if filelist:
                for f in filelist:
                    fname = sublimeutil.normalize_fname(f[0])
                    # Parse only systemVerilog file. Check might be a bit too restrictive ...
                    if fname.lower().endswith(('sv','svh')):
                        tti = verilogutil.get_type_info_file(fname,t)
                        if tti:
                            # print('[struct_assign_completion] Type %s found in %s: %s' %(ti['type'],fname,str(tti)))
                            break
        # print('[struct_assign_completion] tti = %s' % (tti))
        if not tti:
            return []
        c = []
        fe = re.findall(r'(\w+)\s*:',content)
        return self.struct_completion(tti['decl'],True,fe)

    def class_completion(self, fname,cname):
        ci = verilogutil.parse_class_file(fname,cname)
        c = []
        #TODO: parse also the extended class (up to a limit ?)
        for x in ci['member']:
            # filter out local and protected variable
            if 'access' not in x:
                c.append([x['name']+'\t'+x['type'], x['name']])
        for x in ci['function']:
            # filter out local and protected function, and constructor (cannot be called with a .)
            snippet = x['name']+'('
            for i,n in enumerate(x['args'].split(',')):
                if i!=0:
                    snippet += ', '
                snippet += '${{{0}:{1}}}'.format(i+1,n.strip())
            snippet += ')'
            if 'access' not in x and x['name'] != 'new':
                c.append([x['name']+'\tFunction', snippet])
        return c

    def module_completion(self, fname, mname):
        mi = verilogutil.parse_module_file(fname, mname)
        c = []
        # Add instances and signals/IO
        # print('[SV:module_completion] mi = {0}'.format(mi))
        for x in mi['inst']:
            c.append([x['name']+'\t'+x['type'], x['name']])
        for x in mi['port']:
            c.append([x['name']+'\t'+x['type'], x['name']])
        for x in mi['signal']:
            c.append([x['name']+'\t'+x['type'], x['name']])
        return c

    # Interface completion: all signal declaration can be used as completion
    def interface_completion(self,fname, iname, modport_only=False):
        ii = verilogutil.parse_module_file(fname, iname)
        # print(ii)
        c = []
        c_clocking = []
        if not modport_only:
            for x in ii['port']:
                c.append([x['name']+'\tI/O', x['name']])
            for x in ii['signal']:
                if x['tag']=='clocking':
                    c_clocking.append([x['name']+'\tClocking', x['name']])
                else:
                    c.append([x['name']+'\tField', x['name']])
        if 'modport' in ii:
            for x in ii['modport']:
                c.append([x['name']+'\tModport', x['name']])
        if not modport_only:
            for x in ii['param']:
                c.append([x['name']+'\tParam', x['name']])
        if c_clocking:
            c += c_clocking
        return c

    # Provide completion for module binding:
    # Extract all parameter and ports from module definition
    # and filter based on position (parameter or ports) and existing binding
    def module_binding_completion(self,txt,minfo,pos, is_param):
        c = []
        if not minfo:
            return c
        # Extract all exising binding
        b = re.findall(r'\.(\w+)\s*\(',txt,flags=re.MULTILINE)
        # Select parameter or port for completion
        if is_param:
            l = minfo['param']
        else:
            l = minfo['port']
        if not l:
            return c
        # print('[module_binding_completion] Port/param : ' + str(l))
        len_port = max([len(p['name']) for p in l])
        # TODO: find a way to know if the comma need to be inserted or not
        for x in l:
            if x['name'] not in b:
                if is_param:
                    tips = '\t' + str(x['value'])
                    def_val = str(x['value'])
                else:
                    tips = '\t' + str(x['type'])
                    def_val = x['name']
                c.append([x['name']+tips,x['name'].ljust(len_port)+'(${0:' + def_val + '}),'])
        return c

    # Complete case for an enum with all possible value
    def case_completion(self,sig):
        c = []
        (s,el) = VerilogHelper.get_case_template(self.view, sig)
        if s:
            c.append(['case\tcase Template',s])
        return c

    # Completion for ::
    def scope_completion(self,view,r):
        c = []
        # select char before the : and quit with no completion if is not a scope operator
        start_pos = r.a # save original position of the .
        r.b = r.b-1
        start_word = view.substr(view.word(r))
        # print ('Start Word: ' + start_word)
        if start_word != '::' :
            return c
        #Select previous word and get it's type
        r.a -=1
        r.b = r.a
        r = view.word(r);
        w = str.rstrip(view.substr(r))
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
            # print(ti)
            if ti:
                c = [[x['name']+'\t'+x['type'],x['name']] for x in ti]
        elif ti['type'] == 'class':
            sublime.status_message('Autocompletion for class scope unsupported for the moment')
        return c

    # Completion for endfunction, endtask, endclass, endmodule, endpackage, endinterface with label
    def end_completion(self,view,r,prefix):
        re_str = None
        kw = ''
        if prefix == 'end':
            # Extract line to get indentation. Start region one character to the righft to be sure we do not take previous line
            l = self.view.substr(view.line(sublime.Region(r.a+1,r.b)))
            m = re.match(r'(\s*)',l)
            re_str = r'^' + m.groups()[0] + r'((\w+.*)?(begin)\s*(:\s*(\w+))?|(?:virtual\s+)?(function)\s+(?:automatic\s+)?(?:\w+\s+)?(\w+)\s*\(|(class)\s+(\w+)|(module)\s+(\w+)|(package)\s+(\w+)|(interface)\s+(\w+)|(?:virtual\s+)?(task)\s+(\w+)|(case)\s*\((.+)\)|(generate)|(covergroup)\s+(\w+))'
        elif prefix.startswith('endf'):
            re_str = r'function\s+(?:automatic\s+)?(?:\w+\s+)?(\w+)\s*\('
            kw = 'endfunction'
        elif prefix.startswith('endt'):
            re_str = r'task\s+(\w+)'
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
            re_str = r'package\s+(\w+)'
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
            if kw in ['end', 'endcase', 'endmodule', 'endgroup']:
                c_str = kw + ' // ' + name.strip()
            else:
                c_str = kw + ' : ' + name.strip()
        else:
            c_str = kw
        return [[kw+'\t'+c_str,c_str]]


##############################################
#
class VerilogHelper():

    def get_always_template(view):
        settings = view.settings()
        clk_name         = settings.get('sv.clk_name','clk')
        rst_name         = settings.get('sv.rst_name','rst')
        rst_n_name       = settings.get('sv.rst_n_name','rst_n')
        clk_en_name      = settings.get('sv.clk_en_name','clk_en')
        always_name_auto = settings.get('sv.always_name_auto',True)
        always_ce_auto   = settings.get('sv.always_ce_auto',True)
        always_label     = settings.get('sv.always_label',True)
        indent_style     = settings.get('sv.indent_style','1tbs')
        beautifier = verilog_beautifier.VerilogBeautifier(useTab=True, indentSyle=indent_style)
        # try to retrieve name of clk/reset base on buffer content (if enabled in settings)
        if always_name_auto :
            pl = [] # posedge list
            r = view.find_all(r'posedge\s+(\w+)', 0, '$1', pl)
            if pl:
                pl_c = []
                if clk_name not in set(pl):
                    # Make hypothesis that all clock signals have a c in their name
                    pl_c = [x for x in pl if 'c' in x]
                    if pl_c :
                        clk_name = collections.Counter(pl_c).most_common(1)[0][0]
                if rst_name not in set(pl):
                    # Make hypothesis that the reset high signal does not have a 'c' in the name (and that's why active low reset is better :P)
                    pl_r = [x for x in pl if x not in pl_c]
                    if pl_r:
                        rst_name = collections.Counter(pl_r).most_common(1)[0][0]
            nl = [] # negedge list
            r = view.find_all(r'negedge\s+(\w+)', 0, '$1', nl)
            if nl:
                if rst_n_name not in set(pl):
                    rst_n_name = collections.Counter(nl).most_common(1)[0][0]
        if always_ce_auto and clk_en_name != '':
            r = view.find(verilogutil.re_decl+clk_en_name,0)
            if not r :
                clk_en_name = ''
        # define basic always block with asynchronous reset
        a_l = '@(posedge '+clk_name+' or negedge ' + rst_n_name +') begin'
        if always_label :
            a_l +=  ' : proc_$1\n'
        else :
            a_l +=  '\n'
        a_l += '\tif(~'+rst_n_name + ') begin\n'
        a_l += '\t\t$1 <= 0;'
        a_l += '\n\tend else '
        if clk_en_name != '':
            a_l += 'if(' + clk_en_name + ') '
        a_l+= 'begin\n'
        a_l += '\t\t$1 <= $2;'
        a_l+= '\n\tend\nend'
        a_h = a_l.replace('neg','pos').replace(rst_n_name,rst_name).replace('~','')
        a_nr = '@(posedge '+clk_name +') begin'
        if always_label :
            a_nr +=  ' : proc_$1\n\t'
        else :
            a_nr +=  '\n\t'
        if clk_en_name != '':
            a_nr += 'if(' + clk_en_name + ')'
        a_nr+= 'begin\n\t\t$1 <= $2;\n\tend\nend'
        a_l = beautifier.beautifyText(a_l)
        a_h = beautifier.beautifyText(a_l)
        a_nr = beautifier.beautifyText(a_l)
        return (a_l,a_h,a_nr)

    def get_case_template(view, sig_name, ti=None):
        m = re.search(r'(?P<name>\w+)(\s*\[(?P<h>\d+)\:(?P<l>\d+)\])?',sig_name)
        if not m:
            print('[SV:get_case_template] Could not parse ' + sig_name)
            return (None,None)
        if not ti:
            ti = verilogutil.get_type_info(view.substr(sublime.Region(0, view.size())),m.group('name'))
        if not ti['type']:
            print('[SV:get_case_template] Could not retrieve type of ' + m.group('name'))
            return (None,None)
        length = 0
        if m.group('h'):
            length = int(m.group('h')) - int(m.group('l')) + 1
        t = ti['type'].split()[0]
        # print('[get_case_template] ti = {0}'.format(ti))
        if t not in ['enum','logic','bit','reg','wire','input','output']:
            #check first in current file
            tti = verilogutil.get_type_info(view.substr(sublime.Region(0, view.size())),ti['type'], False)
            # Not in current file ? look in index
            if not tti['type']:
                filelist = view.window().lookup_symbol_in_index(ti['type'])
                if filelist:
                    for f in filelist:
                        fname = sublimeutil.normalize_fname(f[0])
                        tti = verilogutil.get_type_info_file(fname,t)
                        if tti:
                            break
            # print('[get_case_template] tti = {0}'.format(tti))
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
            is_sv = os.path.splitext(fname)[1].startswith('.sv')
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
        ti = verilogutil.get_type_info(self.view.substr(sublime.Region(0, self.view.size())),state_next)
        if not ti['type']:
            r = self.view.find(args['ti']['type']+r'.+'+sig_name,0)
            self.view.replace(edit,r,re.sub(r'\b'+sig_name+r'\b',sig_name+', '+state_next,self.view.substr(r)))
