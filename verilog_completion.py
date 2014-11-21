import sublime, sublime_plugin
import re, string, os, sys
import collections

sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
import verilogutil
import sublimeutil

class VerilogAutoComplete(sublime_plugin.EventListener):

    # Cache latest information
    cache_module = {'name' : '', 'date' : 0, 'info' : None}

    def on_query_completions(self, view, prefix, locations):
        # don't change completion if we are not in a systemVerilog file
        if not view.match_selector(locations[0], 'source.systemverilog'):
            return []
        self.view = view
        self.settings = view.settings()
        # Provide completion for most used uvm function: in this case do not override normal sublime completion
        if(prefix.startswith('u')):
            return self.uvm_completion()
        # Provide completion for most always block: in this case do not override normal sublime completion
        if(prefix.startswith('a')):
            return self.always_completion()
        # No additionnal completion if we are inside a word
        if(prefix!=''):
            return []
        # No prefix ? Get previous character and check if it is a '.' , '`' or '$'
        r = view.sel()[0]
        r.a -=1
        t = view.substr(r)
        completion = []
        # Select Competion based on character
        if t=='$':
            completion = self.systemtask_completion()
        elif t=='`':
            completion =  self.tick_completion()
        elif t=='.':
            completion =  self.dot_completion(view,r)
        return (completion, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    def uvm_completion(self):
        c = []
        c.append(['uvm_config_db_get' , 'uvm_config_db#()::get(this, "$1", "$0", $0);' ])
        c.append(['uvm_config_db_set' , 'uvm_config_db#()::set(this, "$1", "$0", $0);' ])
        c.append(['uvm_report_info'   , 'uvm_report_info("$1", "$0", UVM_NONE);' ])
        c.append(['uvm_report_warning', 'uvm_report_warning("$1", "$0");' ])
        c.append(['uvm_report_error'  , 'uvm_report_error("$1", "$0");' ])
        return c

    def always_completion(self):
        c = []
        clk_name    = self.settings.get('sv.clk_name','clk')
        rst_name    = self.settings.get('sv.rst_name','rst')
        rst_n_name  = self.settings.get('sv.rst_n_name','rst_n')
        clk_en_name = self.settings.get('sv.clk_en_name','clk_en')
        print('clk_name = ' + str(clk_name) + ' rst_n_name = ' + str(rst_n_name))
        # try to retrieve name of clk/reset base on buffer content (if enabled in settings)
        if self.settings.get('sv.always_name_auto') :
            pl = [] # posedge list
            r = self.view.find_all(r'posedge\s+(\w+)', 0, '$1', pl)
            if pl:
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
            r = self.view.find_all(r'negedge\s+(\w+)', 0, '$1', nl)
            if nl:
                if rst_n_name not in set(pl):
                    rst_n_name = collections.Counter(nl).most_common(1)[0][0]
        if self.settings.get('sv.always_ce_auto') and clk_en_name != '':
            r = self.view.find(verilogutil.re_decl+clk_en_name,0)
            if not r :
                clk_en_name = ''
        print('clk_name = ' + str(clk_name) + ' rst_n_name = ' + str(rst_n_name))
        # define basic always block with asynchronous reset
        a_l = '@(posedge '+clk_name+' or negedge ' + rst_n_name +') begin : proc_$0\n'
        a_l += '\tif(~'+rst_n_name + ') begin\n\n\tend else '
        if clk_en_name != '':
            a_l += 'if(' + clk_en_name + ') '
        a_l+= 'begin\n\n\tend\nend'
        a_h = a_l.replace('neg','pos').replace(rst_n_name,rst_name).replace('~','')
        a_nr = '@(posedge '+clk_name +') begin : proc_$0\n\t'
        if clk_en_name != '':
            a_nr += 'if(' + clk_en_name + ')'
        a_nr+= 'begin\n\n\tend\nend'
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
            c.append(['always_ff_nr\talways_ff Sync','always_ff '+a_nr])
        if not is_sv or not self.settings.get('sv.always_sv_only') :
            c.append(['always\talways Async','always '+a_l])
            c.append(['alwaysh\talways Async high','always '+a_h])
            c.append(['alwaysc\talways *','always @(*) begin : proc_$0\n\nend'])
            c.append(['always_nr\talways Sync','always_ff '+a_nr])
        return c



    def dot_completion(self,view,r):
        # select word before the dot and quit with no completion if no word found
        start_pos = r.a # save original position of the .
        start_word = view.substr(view.word(r))
        r.a -=1
        r.b = r.a
        r = view.word(r);
        w = str.rstrip(view.substr(r))
        completion = []
        # print ('previous word: ' + w)
        if w=='' or not re.match(r'\w+',w) or start_word.startswith('('):
            #No word before dot => check the scope
            scope = view.scope_name(r.a)
            if 'meta.module.inst' in scope:
                r = sublimeutil.expand_to_scope(view,'meta.module.inst',r)
                txt = view.substr(r)
                mname = re.findall(r'\w+',txt)[0]
                filelist = view.window().lookup_symbol_in_index(mname)
                # TODO: get type to identify if is a module, an interface or a function and use the relevant completion function
                if filelist:
                    completion = self.module_binding_completion(txt, sublimeutil.normalize_fname(filelist[0][0]),mname,start_pos-r.a)
            else :
                return completion
        else :
            # get type information on the variable
            ti = verilogutil.get_type_info(view.substr(sublime.Region(0, view.size())),w)
            # print ('Type info: ' + str(ti))
            if ti['type'] is None:
                return completion
            #Provide completion for different type
            if ti['array']!='None' :
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
                # print (ti['type'])
                filelist = view.window().lookup_symbol_in_index(ti['type'])
                if filelist:
                    fname = sublimeutil.normalize_fname(filelist[0][0])
                    # print(w + ' of type ' + ti['type'] + ' defined in ' + str(fname))
                    # TODO: use a cache system to give better response time
                    with open(fname, 'r') as f:
                        flines = str(f.read())
                    tti = verilogutil.get_type_info(flines,ti['type'])
                    if tti['type']=='interface':
                        return self.interface_completion(flines)
                    elif tti['type']=='enum':
                        completion = self.enum_completion()
                    elif tti['type'] in ['struct','union']:
                        completion = self.struct_completion(tti['decl'])
                    #TODO: Provides more completion (enum, struct, interface, ...)
            #Add randomize function for rand variable
            if ti['decl'].startswith('rand ') or ' rand ' in ti['decl']:
                completion.append(['randomize()','randomize()'])
        return completion

    def array_completion(self,array_type):
        c = []
        if array_type == 'queue':
            c.append(['size'      ,'size()'])
            c.append(['insert'    ,'insert()'])
            c.append(['delete'    ,'delete()'])
            c.append(['pop_front' ,'pop_front()'])
            c.append(['pop_back'  ,'pop_back()'])
            c.append(['push_front','push_front()'])
            c.append(['push_back' ,'push_back()'])
        elif array_type == 'associative':
            c.append(['num'   ,'num()'])
            c.append(['size'  ,'size()'])
            c.append(['delete','delete()'])
            c.append(['exists','exists()'])
            c.append(['first' ,'first()'])
            c.append(['last'  ,'last()'])
            c.append(['next'  ,'next()'])
            c.append(['prev'  ,'prev()'])
        else : # Fixed or dynamic have the same completion
           c.append(['size','size()'])
           c.append(['find','find(x) with(x)'])
           c.append(['find_index','find_index(x) with (x)'])
           c.append(['find_first','find_first(x) with (x)'])
           c.append(['find_last','find_last(x) with (x)'])
           c.append(['unique','unique()'])
           c.append(['uniques','uniques(x) with(x)'])
           c.append(['reverse','reverse()'])
           c.append(['sort','sort()'])
           c.append(['rsort','rsort()'])
           c.append(['shuffle','shuffle()'])
        # Method available to all types of array
        c.append(['min','min()'])
        c.append(['max','max()'])
        c.append(['sum','sum()'])
        c.append(['product','product()'])
        c.append(['and','and()'])
        c.append(['or','or()'])
        c.append(['xor','xor()'])
        return c

    def string_completion(self):
        c = []
        c.append(['len'      , 'len($0)'     ])
        c.append(['substr'   , 'substr($0)'  ])
        c.append(['putc'     , 'putc($0)'    ])
        c.append(['getc'     , 'getc($0)'    ])
        c.append(['toupper'  , 'toupper($0)' ])
        c.append(['tolower'  , 'tolower($0)' ])
        c.append(['compare'  , 'compare($0)' ])
        c.append(['icompare' , 'icompare($0)'])
        c.append(['atoi'     , 'atoi($0)'    ])
        c.append(['atohex'   , 'atohex($0)'  ])
        c.append(['atobin'   , 'atobin($0)'  ])
        c.append(['atoreal'  , 'atoreal($0)' ])
        c.append(['itoa'     , 'itoa($0)'    ])
        c.append(['hextoa'   , 'hextoa($0)'  ])
        c.append(['octoa'    , 'octoa($0)'   ])
        c.append(['bintoa'   , 'bintoa($0)'  ])
        c.append(['realtoa'  , 'realtoa($0)' ])
        return c

    def mailbox_completion(self):
        c = []
        c.append(['num'      , 'num($0)'     ])
        c.append(['get'      , 'get($0)'     ])
        c.append(['try_get'  , 'try_get($0)' ])
        c.append(['peek'     , 'peek($0)'    ])
        c.append(['try_peek' , 'try_peek($0)'])
        c.append(['put'      , 'put($0)'     ])
        c.append(['try_put'  , 'try_put($0)' ])
        return c

    def semaphore_completion(self):
        c = []
        c.append(['get'      , 'get($0)'     ])
        c.append(['try_get'  , 'try_get($0)' ])
        c.append(['put'      , 'put($0)'     ])
        return c

    def process_completion(self):
        c = []
        c.append(['status' , 'status($0)' ])
        c.append(['kill'   , 'kill($0)'   ])
        c.append(['resume' , 'resume($0)' ])
        c.append(['await'  , 'await($0)'  ])
        c.append(['suspend', 'suspend($0)'])
        return c

    def systemtask_completion(self):
        c = []
        c.append(['display'       , 'display("$0",);'       ])
        c.append(['sformatf'      , 'sformatf("$0",)'       ])
        c.append(['test$plusargs' , 'test\$plusargs("$0")'  ])
        c.append(['value$plusargs', 'value\$plusargs("$0",)'])
        c.append(['finish'        , 'finish;'               ])
        #variable
        c.append(['time'          , 'time'               ])
        c.append(['realtime'      , 'realtime'           ])
        c.append(['random'        , 'random'             ])
        c.append(['urandom_range' , 'urandom_range(\$0,)'])
        #cast
        c.append(['cast'          , 'cast($0)'           ])
        c.append(['unsigned'      , 'unsigned($0)'       ])
        c.append(['signed'        , 'signed($0)'         ])
        c.append(['itor'          , 'itor($0)'           ])
        c.append(['rtoi'          , 'rtoi($0)'           ])
        c.append(['bitstoreal'    , 'bitstoreal($0)'     ])
        c.append(['realtobits'    , 'realtobits($0)'     ])
        #assertion
        c.append(['assertoff'     , 'assertoff($0,)'     ])
        c.append(['info'          , 'info("$0");'        ])
        c.append(['error'         , 'error("$0");'       ])
        c.append(['warning'       , 'warning("$0");'     ])
        c.append(['stable'        , 'stable($0)'         ])
        c.append(['fell'          , 'fell($0)'           ])
        c.append(['rose'          , 'rose($0)'           ])
        c.append(['past'          , 'past($0)'           ])
        c.append(['isunknown'     , 'isunknown($0)'      ])
        c.append(['onehot'        , 'onehot($0)'         ])
        c.append(['onehot0'       , 'onehot0($0)'        ])
        #utility
        c.append(['size'          , 'size($0)'           ])
        c.append(['clog2'         , 'clog2("$0",)'       ])
        c.append(['countones'     , 'countones("$0",)'   ])
        c.append(['high'          , 'high($0)'           ])
        c.append(['low'           , 'low($0)'            ])
        #file
        c.append(['fopen'         , 'fopen($0,"r")'      ])
        c.append(['fclose'        , 'fclose($0);'        ])
        c.append(['fflush'        , 'fflush;'            ])
        c.append(['fgetc'         , 'fgetc($0,)'         ])
        c.append(['fgets'         , 'fgets($0,)'         ])
        c.append(['fwrite'        , 'fwrite($0,"")'      ])
        c.append(['readmemb'      , 'readmemb("$0",)'    ])
        c.append(['readmemh'      , 'readmemh("$0",)'    ])
        c.append(['sscanf'        , 'sscanf($0,",)'      ])
        return c

    def tick_completion(self):
        c = []
        c.append(['include'       , 'include "$0"'                ])
        c.append(['define'        , 'define $0'                   ])
        c.append(['ifdef'         , 'ifdef $0'                    ])
        c.append(['ifndef'        , 'ifndef $0'                   ])
        c.append(['else'          , 'else '                       ])
        c.append(['elsif'         , 'elsif $0'                    ])
        c.append(['endif'         , 'endif'                       ])
        c.append(['celldefine'    , 'celldefine $0 endcelldefine' ])
        c.append(['endcelldefine' , 'endcelldefine '              ])
        c.append(['line'          , 'line '                       ])
        c.append(['resetall'      , 'resetall'                    ])
        c.append(['timescale'     , 'timescale $0'                ])
        c.append(['undef'         , 'undef $0'                    ])
        return c

    def enum_completion(self):
        c = []
        c.append(['first', 'first()'])
        c.append(['last' , 'last()' ])
        c.append(['next' , 'next()' ])
        c.append(['prev' , 'prev()' ])
        c.append(['num'  , 'num()'  ])
        c.append(['name' , 'name()' ])
        return c

    def struct_completion(self,decl):
        c = []
        # extract fields from the declaration
        m = re.search(r'\{(.*)\}', decl)
        if m is not None:
            # print (m.groups()[0])
            fl = re.findall(r"(\w+)\s*;",m.groups()[0])
            for f in fl:
                c.append([f,f])
        return c

    # Interface completion: all signal declaration can be used as completion
    def interface_completion(self,flines):
        flines = verilogutil.clean_comment(flines)
        # Look all modports
        modports = re.findall(r'^\s*modport\s+(\w+)\b', flines, flags=re.MULTILINE)
        # remove modports before looking for I/O and field to avoid duplication of signals
        flines = re.sub(r'modport\s+\w+\s+\(.*?\);','',flines, flags=re.MULTILINE|re.DOTALL)
        # remove cloking block input
        flines = re.sub(r'clocking\b.*?endclocking(\s*:\s*\w+)?','',flines, flags=re.MULTILINE|re.DOTALL)
        #Look for signal declaration
        int_decl = r'(?<!@)\s*(?:^|,|\()\s*(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w:\.]*\s+)(\[[\w:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*)\b\s*(?:;|\))'
        mlist = re.findall(int_decl, flines, flags=re.MULTILINE)
        c = []
        # print('Declarations founds: ',mlist)
        if mlist is not None:
            # for each matched declaration extract only the signal name.
            # Each declaration can be a list => split it
            # it can included default initialization => remove it
            for m in mlist:
                slist = re.findall(r'([A-Za-z_][\w]*)\s*(\=\s*\w+)?(,|$)',m[5])
                # print('Parsing ',str(m[5]),' with type ' + m[0] +' => ',str(slist))
                # Provide information on the type of signal : I/O, parameter or field
                if m[0].strip() in ['input', 'output', 'inout']:
                    t = 'I/O'
                elif m[0].strip() == 'parameter':
                    t = 'Param'
                else :
                    t = 'Field'
                if slist is not None:
                    for s in slist:
                        c.append([s[0]+'\t'+t,s[0]])
        # Completion for modports:
        if modports:
            for mp in modports:
                c.append([mp+'\tModport',mp])
        return c

    # Provide completion for module binding:
    # Extract all parameter and ports from module definition
    # and filter based on position (parameter or ports) and existing binding
    def module_binding_completion(self,txt,fname,mname,pos):
        c = []
        # Extract all parameter and ports from module definition using cached information if available
        fdate = os.path.getmtime(fname)
        if self.cache_module['name'] == fname and self.cache_module['date']==fdate:
            minfo = self.cache_module['info']
        else:
            minfo = verilogutil.parse_module(fname,mname)
            self.cache_module['info']  = minfo
            self.cache_module['name'] = fname
            self.cache_module['date'] = fdate
        # print('[module_binding_completion] Module ' + mname + ' : ' + str(minfo))
        if not minfo:
            return c
        # Extract all exising binding
        b = re.findall(r'\.(\w+)\s*\(',txt,flags=re.MULTILINE)
        # Find position of limit between parameter and port
        l = minfo['port']
        if minfo['param']:
            m = re.search(r'\)\s*\(',txt,flags=re.MULTILINE)
            if m:
                if m.start()>pos:
                    l = minfo['param']
        len_port = max([len(p['name']) for p in minfo['port']])
        # TODO: find a way to know if the comma need to be inserted or not
        for x in l:
            if x['name'] not in b:
                c.append([x['name']+'\t'+str(x['type']),x['name'].ljust(len_port)+'(' + x['name'] + '$0),'])
        return c
