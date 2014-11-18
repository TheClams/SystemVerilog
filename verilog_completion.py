import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
import verilogutil

class VerilogAutoComplete(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        # don't change completion if we are not in a systemVerilog file
        if not view.match_selector(locations[0], 'source.systemverilog'):
            return []
        # Provide completion for most used uvm function: in this case do not override normal sublime completion
        if(prefix.startswith('u')):
            return self.uvm_completion()
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

    def dot_completion(self,view,r):
        # select word before the dot and quit with no completion if no word found
        r.a -=1
        r.b = r.a
        r = view.word(r);
        w = str.rstrip(view.substr(r))
        completion = []
        # print ('previous word: ' + w)
        if w=='': #No word before dot => no completion
            return completion
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
                fname = filelist[0][0]
                #filename seems to be in a unix specific format => convert to windows if needed
                if sublime.platform() == 'windows':
                    fname= re.sub(r'/([A-Za-z])/(.+)', r'\1:/\2', fname)
                    fname= re.sub(r'/', r'\\', fname)
                # print(w + ' of type ' + ti['type'] + ' defined in ' + str(fname))
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
        int_decl = r'(?<!@)\s*(?:^|,|\()\s*(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w:\.]*\s+)(\[[\w:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*)\b\s*(?:;|\))'
        flines = verilogutil.clean_comment(flines)
        mlist = re.findall(int_decl, flines, flags=re.MULTILINE)
        c = []
        # print('Declarations founds: ',mlist)
        if mlist is not None:
            # for each matched declaration extract only the signal name.
            # Each declaration can be a list => split it
            # it can included default initialization => remove it
            for m in mlist:
                slist = re.findall(r'([A-Za-z_][\w]*)\s*(\=\s*\w+)?(,|$)',m[5])
                # print('Parsing ',str(m[5]),' => ',str(slist))
                if slist is not None:
                    for s in slist:
                        c.append([s[0],s[0]])
        return c
