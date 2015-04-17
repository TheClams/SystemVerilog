import argparse
import re
import string
import verilogutil

class VerilogBeautifier():

    def __init__(self, nbSpace=3, useTab=False, oneBindPerLine=True, oneDeclPerLine=False, paramOneLine=True, indentSyle='1tbs'):
        self.settings = {'nbSpace': nbSpace, \
                        'useTab':useTab, \
                        'oneBindPerLine':oneBindPerLine, \
                        'oneDeclPerLine':oneDeclPerLine,\
                        'paramOneLine': paramOneLine,\
                        'indentSyle' : indentSyle}
        self.indentSpace = ' ' * nbSpace
        if useTab:
            self.indent = '\t'
        else:
            self.indent = self.indentSpace
        self.states = []
        self.state = ''
        self.re_decl = re.compile(r'^[ \t]*(\w+\:\:)?([A-Za-z_]\w*)[ \t]+(signed|unsigned\b)?[ \t]*(\[([\w\:\-\+></` \t]+)\])?[ \t]*([A-Za-z_][\w\[\]]*)[ \t]*(\[([\w\:\-\+></\$` \t]+)\])?[ \t]*(,[\w, \t]*)?;[ \t]*(.*)')
        self.re_inst = re.compile(r'(?s)^\s*\b(?P<itype>\w+)\s*(#\s*\([^;]+\))?\s*\b(?P<iname>\w+)\s*\(',re.MULTILINE)

    def getIndentLevel(self,txt):
        line = txt[:txt.find('\n')]
        # Make sure there is no mix tab/space
        if self.settings['useTab']:
            line = line.replace(self.indentSpace,'\t')
        else:
            line = line.replace('\t',self.indentSpace)
        cnt = len(line) - len(line.lstrip())
        if not self.settings['useTab']:
            cnt = int(cnt/self.settings['nbSpace'])
        return cnt

    def stateUpdate(self,newState=None):
        if newState:
            self.states.append(newState)
        else:
            self.states.pop()
        # Get current state from the list
        if not self.states:
            self.state = ''
        else:
            self.state = self.states[-1]

    def isStateEnd(self,w):
        return (self.state=='begin' and w=='end') or (self.state=='covergroup' and w=='endgroup') or (self.state=='fork' and w.startswith('join')) or (self.state=='{' and w=='}') or (self.state=='(' and w==')') or (self.state and w=='end' + self.state)

    def beautifyFile(self,fnameIn,fnameOut=''):
        if not fnameOut:
            fnameOut = fnameIn
        with open(fnameIn, "r") as f:
            txt = f.read()
        txt = self.beautifyText(txt)
        with open(fnameOut, "w") as f:
            f.write(txt)

    def beautifyText(self,txt):
        # Variables
        self.states = [] # block indent list
        w_d = ['','\n'] # previous word
        line = '' # current line
        block = '' # block of text to align
        self.block_state = ''
        block_handled = False
        block_ended = False
        txt_new = '' # complete text beautified
        ilvl = self.getIndentLevel(txt)
        ilvl_prev = ilvl
        has_indent = ilvl!=0
        line_cnt = 1
        split = {}
        split_always = 0
        self.always_state = ''
        # Split all text in word, special character, space and line return
        words = re.findall(r"\w+|[^\w\s]|[ \t]+|\n", txt, flags=re.MULTILINE)
        for w in words:
            state_end = self.isStateEnd(w)
            # Start of line ?
            if w_d[-1]=='\n':
                ilvl_prev = ilvl
                if not w.strip():
                    if w!='\n' and self.block_state in ['module']:
                        block+=w
                    has_indent = w!='\n'
                if state_end:
                    self.stateUpdate()
                    assert ilvl>0, '[Beautify] Block end with already no indentation ! Line {line_cnt:4}: "{line:<150}" => state={state:<16} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state)
                    ilvl-=1
                # Handle end of self.block_state
                if self.block_state=='assign' and w!='assign' and not re.match(r'[\t ]+',w):
                    txt_new += self.alignAssign(block,2)
                    block = ''
                    self.block_state = ''
                # Insert indentation except for comment_block without initial indentation and module declaration
                if self.block_state not in ['module'] and (self.state!='comment_block' or has_indent) and w.strip():
                    ilvl_tmp = ilvl+split_always
                    for i,x in split.items() :
                        ilvl_tmp += x[0]
                    # print('split={split} states={s} block={b} => ilvl = {i}'.format(split=split,i=ilvl+split_sum,s=self.states, b=self.block_state))
                    line = ilvl_tmp * self.indent
            # Handle end of split
            if ilvl in split:
                if self.state not in ['comment_line','comment_block'] and w in [';','end'] :
                    # print('[Beautify] End Split on line {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=self.block_state, ilvl=ilvl))
                    split.pop(ilvl,0)
            if w=='\n':
                block_ended = False
                # print('[Beautify] {line_cnt:4}: ilvl={ilvl} state={state} bs={bstate} as={astate} split={split}'.format(line_cnt=line_cnt, state=self.states, bstate=self.block_state, astate=self.always_state, ilvl=ilvl, split=split))
                # print(line)
                # Search for split line requiring temporary increase of the indentation level
                if self.state not in ['comment_block','{'] and self.block_state not in ['module','instance','struct']:
                    if self.state == 'comment_line' and len(self.states)>1 and self.states[-2] == '{':
                        tmp = None
                    else :
                        tmp = verilogutil.clean_comment(line).strip()
                    if tmp:
                        m = re.search(r'(;|\{|\bend|\bendcase)$|^\}$|(begin(\s*\:\s*\w+)?)$|(case)\s*\(.*\)$|(`\w+)\s*(\(.*\))?$|^(`\w+)\b',tmp)
                        # print('[Beautify] Testing for split: "{0}" (ilvl={1} prev={2})'.format(tmp,ilvl,ilvl_prev))
                        if not m:
                            if tmp.startswith('always'):
                                split_always = 1
                                # print('[Beautify] Always split on line {line_cnt:4} => state={block_state}.{state}: "{line:<140}"'.format(line_cnt=line_cnt, line=line, state=self.states, block_state=self.block_state, ilvl=ilvl))
                            elif (ilvl==ilvl_prev or tmp.startswith('end')) and self.state != '(' :
                                if ilvl not in split:
                                    # print('[Beautify] First split at ilvl {ilvl} on line {line_cnt:4} => state={block_state}.{state}: "{line:<140}"'.format(line_cnt=line_cnt, line=line, state=self.states, block_state=self.block_state, ilvl=ilvl))
                                    split[ilvl] = [1,tmp]
                                else :
                                    m = re.match(r'^\s*(assign\s+)?\w+\s*(<?=)\s*(.*)',split[ilvl][1])
                                    if not m:
                                        # print('[Beautify] Incrementing split at ilvl {ilvl} on line {line_cnt:4} => state={block_state}.{state}: "{line:<140}"'.format(line_cnt=line_cnt, line=line, state=self.states, block_state=self.block_state, ilvl=ilvl))
                                        split[ilvl][0] += 1
                if self.block_state == 'decl' and not self.re_decl.match(line.strip()):
                    txt_new += self.alignDecl(block)
                    block = ''
                    self.block_state = ''
                # print('[Beautify] {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=self.block_state, ilvl=ilvl))
                block += line.rstrip() + '\n'
                line = ''
                line_cnt+=1
            # else:
            elif not w_d[-1]=='\n' or w.strip():
                if self.state not in ['comment_line','comment_block'] and self.settings['indentSyle']=='gnu':
                    if w == 'begin' and line.strip()!='':
                        ilvl_tmp = ilvl+split_always+1
                        for i,x in split.items() :
                            ilvl_tmp += x[0]
                        if ilvl not in split:
                            tmp = verilogutil.clean_comment(line).strip()
                            # print('[Beautify] Adding split at ilvl {ilvl} on line {line_cnt:4} => state={block_state}.{state}: "{line:<140}"'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=self.block_state, ilvl=ilvl))
                            split[ilvl] = [1,tmp]
                        else:
                            split[ilvl][0] += 1
                        line += '\n' + ilvl_tmp * self.indent
                    elif w == 'else' and w_d[-1]!='\n' and w_d[-2]=='end':
                        ilvl_tmp = ilvl+split_always
                        for i,x in split.items() :
                            ilvl_tmp += x[0]
                        line += '\n' + ilvl_tmp * self.indent
                # Insert line return after a block ended if this is no a comment
                if block_ended and w.strip() and (w != '/' or w_d[-1] != '/'):
                    line = line.rstrip() + '\n'
                    block_ended = False
                line += w
                if self.state not in ['comment_line','comment_block']:
                    # print('State={0}.{1} -- Testing {2}'.format(self.state,self.block_state,block+line))
                    action = self.processWord(w,w_d[-1], state_end, block + line)
                    if action.startswith("incr_ilvl"):
                        ilvl+=1
                        if action == "incr_ilvl_flush":
                            txt_new += block
                            block = line
                            line = ''
            # Handle the self.block_state and call appropriate alignement function
            if w==';' and self.state not in ['comment_line','comment_block', '(']:
                if self.block_state in ['text','decl'] and self.re_decl.match(line.strip()):
                    self.block_state = 'decl'
                    # print('Setting Block state to decl on line "{0}"'.format(line))
                elif self.block_state in ['module','instance','text','package','decl'] or (self.block_state in ['struct','struct_assign'] and self.state!='{'):
                    # print('Aligning block {0}'.format(self.block_state))
                    if self.block_state=='module':
                        block_tmp = self.alignModulePort(block+line,ilvl-1)
                        line = ''
                        block_ended = True
                    elif self.block_state=='instance':
                        block_tmp = self.alignInstance(block+line,ilvl)
                        line = ''
                    elif self.block_state=='struct':
                        block_tmp = self.alignDecl(block+line)
                        line = ''
                    elif self.block_state=='struct_assign':
                        block_tmp = self.alignAssign(block+line,1)
                        line = ''
                    elif self.block_state=='decl':
                        block_tmp = self.alignDecl(block)
                    else:
                        block_tmp = block + line
                        line = ''
                    if not block_tmp:
                        print('[Beautify: ERROR] Unable to extract a {0} from "{1}"'.format(self.block_state,block))
                    else:
                        block = block_tmp
                    self.block_state = ''
                    block_handled = True
            # Handle the end of self.state
            if state_end:
                # Check if this was not already handled
                # print('[Beautify] state {0}.{1} end on word {2}'.format(self.states,self.block_state,w))
                if self.block_state == 'generate' :
                    m = self.re_inst.search(block[9:])
                    block_tmp = block
                    for m in self.re_inst.finditer(block[9:]):
                        if m and m.group('itype') not in ['else', 'begin', 'end'] and m.group('iname') not in ['if','for','foreach']:
                            inst_start = 9+m.start()
                            inst_end = block.find(';',inst_start)+1;
                            if(inst_end>inst_start):
                                inst_block = block[inst_start:inst_end]
                                inst_ilvl = self.getIndentLevel(inst_block)
                                inst_block_aligned = self.alignInstance(inst_block,inst_ilvl)
                                block_tmp = block_tmp.replace(inst_block,inst_block_aligned)
                                # print('[Beautify] Align block inst in generate : ilvl={0}'.format(inst_ilvl))
                    block = block_tmp
                elif w in ['endtask', 'endfunction']:
                    block = self.alignAssign(block+line,1)
                    line = ''
                    block_handled = True
                if w_d[-1]!='\n':
                    self.stateUpdate()
                    assert ilvl>0, '[Beautify] Block end with already no indentation ! Line {line_cnt:4}: "{line:<150}" => state={state:<16} '.format(line_cnt=line_cnt, line=line, state=self.state)
                    ilvl-=1
            # Comment: do not try to recognise words, just end of the comment
            elif self.state=='comment_line':
                if w=='\n':
                    self.stateUpdate()
                    if not self.block_state:
                        block_handled = True
            elif self.state=='comment_block':
                if w_d[-1]=='*' and w=='/':
                    self.stateUpdate()
                    block += line
                    line = ''
                    if not self.block_state:
                        block_handled = True
            #
            else :
                if w_d[-1]=='/':
                    if w=='/':
                        self.stateUpdate('comment_line')
                        block_ended = False
                    elif w=='*':
                        self.stateUpdate('comment_block')
                        block_ended = False
                    if line.strip() in ["//", "/*"] and not has_indent:
                        line = line.strip()
                    # print('[Beautify] state={self.block_state:<16}.{state:<16} -- ilvl={ilvl} -- {line_cnt:4}: "{line}" '.format(line_cnt=line_cnt, line=line, state=self.state, block_state=self.block_state, ilvl=ilvl))
            if self.block_state == 'always' and (not self.state or self.state in ['module','interface']):
                tmp = verilogutil.clean_comment(block + line).strip()
                m = re.match(r'(?s)^\s*always\w*\s+(@\s*(\*|\([^\)]*\)))?\s*begin',tmp, flags=re.MULTILINE)
                if (m and w=='end') or (self.always_state in ['else',''] and w in ['end',';']):
                    block = self.alignAssign(block+line,7)
                    line = ''
                    block_handled = True
                    self.always_state = ''
                    split_always = 0
                    # print('[Beautify] End of always block at line {0}: \n{1}'.format(line_cnt,block))
                elif not m :
                    if w == 'else':
                        # print('[Beautify] Inside else part of always at line {0}'.format(line_cnt))
                        self.always_state = 'else'
                    # handle case of always if() ...; without else
                    elif self.always_state == 'expect_else' and w.strip() and w != '/':
                        block = (block + line)
                        last_sc = block.rfind(';') + 1
                        last_end = block.rfind('end') + 3
                        if last_end < last_sc:
                            last_end = last_sc
                        line = block[last_end:]
                        block = block[:last_end]
                        # remove extra indent when the always end block is discovered too late
                        if split_always == 1:

                            line = re.sub(r'^'+self.indent,'',line,flags=re.MULTILINE)
                            # print('[Beautify] End of always block at line {0}, extracting {1}'.format(line_cnt,line))
                            self.block_state = ''
                            action = self.processWord(w,w_d[-1],state_end, line)
                            if action.startswith("incr_ilvl"):
                                ilvl+=1
                                if action == "incr_ilvl_flush":
                                    txt_new += block
                                    block = line
                                    line = ''
                        block = self.alignAssign(block,7)
                        # print('[Beautify] End of always block at line {0} with word {1}: \n{2}'.format(line_cnt,w,block))
                        if not w.startswith('always'):
                            self.always_state = ''
                        txt_new += block
                        block = ''
                        split_always = 0
                    elif w == 'if':
                        self.always_state = 'if'
                        # print('[Beautify] Inside if part of always at line {0}'.format(line_cnt))
                    elif self.always_state == 'if' and w in ['end',';']:
                        # print('[Beautify] End of if part=> next word has to be an else'.format(line_cnt))
                        self.always_state = 'expect_else'
            # Add block to the text
            if block_handled:
                # print('[Beautify] state={block_state}.{state} Block handled:\n"{block}" '.format(state=self.state, block_state=self.block_state, block=block))
                txt_new += block
                block = ''
                self.block_state = ''
                block_handled = False
            # Keep previous words
            if w.strip() or w_d[-1]!='\n':
                w_d[-2] = w_d[-1]
                w_d[-1] = w
        # Check that there is no reminding stuff todo:
        block = block+line
        # print('[Beautify] state={block_state}.{state}\n{block} '.format(state=self.state, block_state=self.block_state, block=block))
        if self.block_state in ['module','instance','text','package','decl', 'assign'] or (self.block_state in ['struct','struct_assign'] and self.state!='{'):
            if self.block_state=='module':
                block_tmp = self.alignModulePort(block,ilvl-1)
            elif self.block_state=='instance':
                block_tmp = self.alignInstance(block,ilvl)
            elif self.block_state=='struct':
                block_tmp = self.alignDecl(block)
            elif self.block_state=='assign':
                block_tmp = self.alignAssign(block,2)
            elif self.block_state=='struct_assign':
                block_tmp = self.alignAssign(block,1)
            elif self.block_state=='decl':
                block_tmp = self.alignDecl(block)
            else:
                block_tmp = block
            if not block_tmp:
                print('[Beautify: ERROR] Unable to extract a {0} from "{1}"'.format(self.block_state,block))
            else:
                block = block_tmp
        txt_new += block
        return txt_new

    def processWord(self,w, w_prev, state_end, txt):
        kw_block = ['module', 'class', 'interface', 'program', 'function', 'task', 'package', 'case', 'generate', 'covergroup', 'fork', 'begin', '{', '(']
        if w in kw_block:
            self.stateUpdate(w)
            if w in ['module','package', 'generate', 'function', 'task']:
                self.block_state = w
                return "incr_ilvl_flush"
            else:
                return "incr_ilvl"
        # Identify self.block_state
        if not self.block_state:
            if w in ['assign']:
                self.block_state = w
            elif w.startswith('always'):
                self.block_state = 'always'
                self.always_state = ''
                # print('Start of always block')
            elif w_prev=='\n' and w!= '/' and not state_end:
                # print('Start of text block with "{0}"'.format(w))
                self.block_state = 'text'
        elif self.block_state=='text':
            tmp = verilogutil.clean_comment(txt).strip()
            m = self.re_inst.match(tmp)
            if m and m.group('itype') not in ['else', 'begin', 'end'] and m.group('iname') not in ['if','for','foreach']:
                self.block_state = 'instance'
            elif re.match(r'\s*\b(typedef\s+)?(struct|union)\b',tmp, flags=re.MULTILINE):
                self.block_state = 'struct'
            elif re.match(r"(?s)^.*=\s*'\{",tmp, flags=re.MULTILINE):
                # print('Matching struct assign on "{0}"'.format(txt))
                self.block_state = 'struct_assign'
        # print('Test "{0}" => {1}.{2}.{3}'.format((txt).strip(),self.states,self.block_state,self.always_state))
        return ""

    # Align ANSI style port declaration of a module
    def alignModulePort(self,txt, ilvl):
        # Extract parameter and ports
        m = re.search(r'(?s)(?P<module>^[ \t]*module)\s*(?P<mname>\w+)\s*(?P<paramsfull>#\s*\(\s*(?P<params>.*)\s*\))?\s*\(\s*(?P<ports>.*)\s*\)\s*;$',txt,flags=re.MULTILINE)
        if not m:
            return ''
        txt_new = self.indent*(ilvl) + 'module ' + m.group('mname').strip()
        # Add optional parameter declaration
        if m.group('params'):
            param_txt = m.group('params').strip()
            # param_txt = re.sub(r'(^|,)\s*parameter','',param_txt) # remove multiple parameter declaration
            re_param = re.compile(r'^[ \t]*(?P<parameter>parameter\s+)?(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<param>\w+)\b\s*=\s*(?P<value>[\w\:`\']+)\s*(?P<sep>,)?[ \t]*(?P<list>\w+\s*=\s*\w+(,)?\s*)*(?P<comment>.*?$)',flags=re.MULTILINE)
            decl = re_param.findall(param_txt)
            # print(decl)
            len_type  = max([len(x[1]) for x in decl if x not in ['signed','unsigned']])
            len_sign  = max([len(x[2]) for x in decl])
            len_bw    = max([len(x[4]) for x in decl])
            len_param = max([len(x[5]) for x in decl])
            len_value = max([len(x[6]) for x in decl])
            len_comment = max([len(x[10]) for x in decl])
            has_param_list = ['' for x in decl if x[0] != '']
            has_param_all = len(has_param_list)==len(decl)
            has_param = len(has_param_list)>0
            # print(str((len_type,len_sign,len_bw,len_param,len_value,len_comment,has_param_all,has_param)))
            txt_new += ' #('
            # add only one parameter statement if there is at least one but not on all line
            if has_param and not has_param_all:
                txt_new += 'parameter'
            # If not on one line align parameter together, otherwise keep as is
            if '\n' in param_txt or not self.settings['paramOneLine']:
                txt_new += '\n'
                lines = param_txt.splitlines()
                for i,line in enumerate(lines):
                    # ignore the first line with parameter keyword only since it has already been added
                    if i==0 and line.strip()=='parameter':
                        continue
                    txt_new += self.indent*(ilvl+1)
                    m_param = re_param.search(line.strip())
                    if not m_param :
                        # print('Line {0} is not a parameter definition'.format(line.strip()))
                        txt_new += line.strip()
                    else:
                        if has_param_all:
                            txt_new += 'parameter '
                        if len_type>0:
                            if m_param.group('type'):
                                if m_param.group('type') not in ['signed','unsigned']:
                                    txt_new += m_param.group('type').ljust(len_type+1)
                                else:
                                    txt_new += ''.ljust(len_type+2) + m_param.group('type').ljust(len_sign+1)
                            else:
                                txt_new += ''.ljust(len_type+2)
                        if len_sign>0:
                            if m_param.group('sign'):
                                txt_new += m_param.group('sign').ljust(len_sign)
                            else:
                                txt_new += ''.ljust(len_sign+1)
                        if len_bw>0:
                            if m_param.group('bw'):
                                txt_new += '[' + m_param.group('bw').rjust(len_bw) + '] '
                            else:
                                txt_new += ''.ljust(len_bw+3)
                        txt_new += m_param.group('param').ljust(len_param)
                        txt_new += ' = ' + m_param.group('value').ljust(len_value)
                        if m_param.group('sep') and (i!=(len(lines)-1) or m_param.group('list')):
                            txt_new += m_param.group('sep')
                        #TODO: in case of list try to do something: option to split line by line? align in column if multiple list present ?
                        if m_param.group('list'):
                            txt_new += ' ' + m_param.group('list')
                        if i==(len(lines)-1) and m_param.group('comment'):
                            txt_new += ' '
                        if m_param.group('comment'):
                            txt_new += ' ' + m_param.group('comment')
                    txt_new += '\n' + self.indent*(ilvl)
            else :
                if has_param and not has_param_all:
                    txt_new += ' '
                txt_new += param_txt
                # print('len Comment = ' + str(len_comment)+ ': ' + str([x[9] for x in decl])+ '"')
                if len_comment > 0 :
                    txt_new += '\n' + self.indent*(ilvl)
            txt_new += ')'
            #
        # Handle special case of no ports
        if not m.group('ports'):
            return txt_new + '();'
        # Add port list declaration
        txt_new += ' (\n'
        # Port declaration: direction type? signess? buswidth? list ,? comment?
        re_str = r'^[ \t]*(?P<dir>[\w\.]+)[ \t]+(?P<var>var\b)?[ \t]*(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<ports>(?P<port1>\w+)[\w, \t]*)[ \t]*(?P<comment>.*)'
        # handle case of multiple input/output declared on same line
        txt_port = re.sub(r'\s*,\s*(input|output|inout)\b\s+',r',\n\1 ',m.group('ports'))
        decl = re.findall(re_str,txt_port,flags=re.MULTILINE)
        # Extract max length of the different field for vertical alignement
        port_dir_l = [x[0] for x in decl if x[0] in verilogutil.port_dir]
        port_if_l  = [x[0] for x in decl if x[0] not in verilogutil.port_dir]
        # Get Direction length, if any
        len_dir = 0
        if port_dir_l:
            len_dir  = max([len(x) for x in port_dir_l])
        # Get IF length, if any
        len_if = 0
        if port_if_l:
            len_if  = max([len(x) for x in port_if_l])
        # Get Var length, if any
        len_var = 0
        for x in decl:
            if x[1] != '':
                len_var = 3
        # Get Var length, if any
        port_bw_l  = [re.sub(r'\s*','',x[5]) for x in decl]
        len_bw = 0
        if len(port_bw_l)>0:
            len_bw  = max([len(x) for x in port_bw_l])
        #max_port_len = max([len(re.sub(r',',', ',re.sub(r'\s*','',x[6])))-2 for x in decl])
        max_port_len = max([len(x[7]) for x in decl])
        len_sign = 0
        len_type = 0
        len_type_user = 0
        for x in decl:
            if x[1] == '' and x[3]=='' and x[4]=='' and x[2] not in ['logic', 'wire', 'reg', 'signed', 'unsigned']:
                if len_type_user < len(x[2]) :
                    len_type_user = len(x[2])
            else :
                if len_type < len(x[2]) and  x[2] not in ['signed','unsigned']:
                    len_type = len(x[2])
            if x[2] in ['signed','unsigned'] and len_sign<len(x[2]):
                len_sign = len(x[2])
            elif x[3] in ['signed','unsigned'] and len_sign<len(x[3]):
                len_sign = len(x[3])
        len_type_full = len_type
        if len_var > 0 or len_bw > 0 or len_sign > 0 :
            if len_type > 0:
                len_type_full +=1
            if len_var > 0:
                len_type_full += 4
            if len_bw > 0:
                len_type_full += 2+len_bw
            if len_sign > 0:
                len_type_full += 1+len_sign
        max_len = len_type_full
        if len_type_user < len_type_full:
            len_type_user = len_type_full
        else :
            max_len = len_type_user
        # Adjust IF length compare to the other
        if len_if < max_len+len_dir+1:
            len_if = max_len+len_dir+1
        else :
            max_len = len_if-len_dir-1
        if len_type_user < max_len:
            len_type_user = max_len
        # print('Len:  dir=' + str(len_dir) + ' if=' + str(len_if) + ' type=' + str(len_type) + ' sign=' + str(len_sign) + ' bw=' + str(len_bw) + ' type_user=' + str(len_type_user) + ' port=' + str(max_port_len) + ' max_len=' + str(max_len) + ' len_type_full=' + str(len_type_full))
        # Rewrite block line by line with padding for alignment
        lines = txt_port.splitlines()

        for i,line in enumerate(lines):
            # Remove leading and trailing space.
            l = line.strip()
            # ignore empty line at the begining and the end of the connection
            if (i!=(len(lines)-1) and i!=0) or l !='':
                m_port = re.search(re_str,l)
                txt_new += self.indent*(ilvl+1)
                if m_port:
                    # For standard i/o
                    if m_port.group('dir') in verilogutil.port_dir :
                        txt_new += m_port.group('dir').ljust(len_dir)
                        # Align userdefined type differently from the standard type
                        if m_port.group('var') or m_port.group('sign') or m_port.group('bw') or m_port.group('type') in ['logic', 'wire', 'reg', 'signed', 'unsigned']:
                            if len_var>0:
                                if m_port.group('var'):
                                    txt_new += ' ' + m_port.group('var')
                                else:
                                    txt_new += ' '.ljust(len_var+1)
                            if len_type>0:
                                if m_port.group('type'):
                                    if m_port.group('type') not in ['signed','unsigned']:
                                        txt_new += ' ' + m_port.group('type').ljust(len_type)
                                    else:
                                        txt_new += ''.ljust(len_type+1) + ' ' + m_port.group('type').ljust(len_sign)
                                else:
                                    txt_new += ''.ljust(len_type+1)
                                # add sign space it exists at least for one port
                                if len_sign>0:
                                    if m_port.group('sign'):
                                        txt_new += ' ' + m_port.group('sign').ljust(len_sign)
                                    elif m_port.group('type') not in ['signed','unsigned']:
                                        txt_new += ''.ljust(len_sign+1)
                            elif len_sign>0:
                                if m_port.group('type') in ['signed','unsigned']:
                                    txt_new += ' ' + m_port.group('type').ljust(len_sign)
                                elif m_port.group('sign'):
                                    txt_new += ' ' + m_port.group('sign').ljust(len_sign)
                                else:
                                    txt_new += ''.ljust(len_sign+1)
                            # Add bus width if it exists at least for one port
                            if len_bw>1:
                                if m_port.group('bw'):
                                    txt_new += ' [' + m_port.group('bw').strip().rjust(len_bw) + ']'
                                else:
                                    txt_new += ''.rjust(len_bw+3)
                            if max_len > len_type_full:
                                txt_new += ''.ljust(max_len-len_type_full)
                        elif m_port.group('type') :
                            txt_new += ' ' + m_port.group('type').ljust(len_type_user)
                        elif len_type_user>0 :
                            txt_new += ' '.ljust(len_type_user+1)
                    # For interface
                    else :
                        txt_new += m_port.group('dir').ljust(len_if)
                    # Add port list: space every port in the list by just on space
                    s = re.sub(r'\s*,\s*',', ',m_port.group('ports'))
                    txt_new += ' '
                    if s.endswith(', '):
                        txt_new += s[:-2].ljust(max_port_len)
                        if i!=(len(lines)-1):
                            txt_new += ','
                    else:
                        txt_new += s.ljust(max_port_len) + ' '
                    # Add comment
                    if m_port.group('comment') :
                        txt_new += ' ' + m_port.group('comment')
                else : # No port declaration ? recopy line with just the basic indentation level
                    # Look for a simple comment line and check its indentation: if too large, align with port comment position
                    m_comment = re.search(r'\s*//.*',l)
                    if m_comment:
                        ilvl_comment = self.getIndentLevel(line)
                        if ilvl_comment > (ilvl+2):
                            txt_new += ''.rjust(len_if+1+max_port_len+2) + l.strip()
                        else:
                            txt_new += l
                    else:
                        txt_new += l
                # Remove trailing spaces/tabs and add the end of line
                txt_new = txt_new.rstrip(' \t') + '\n'
        txt_new += self.indent*(ilvl) + ');'
        return txt_new

    # Alignement for case/structure assign : "word: statement"
    def alignAssign(self,txt, mask_op):
        #TODO handle array
        re_str_l = []
        if mask_op & 1:
            re_str_l.append(r'^[ \t]*(?P<scope>\w+\:\:)?(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>\:(?!\:))\s*(?P<statement>.*)$')
        if mask_op & 2:
            re_str_l.append(r'^[ \t]*(?P<scope>assign)\s+(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>=)\s*(?P<statement>.*)$')
        if mask_op & 4:
            re_str_l.append(r'^[ \t]*(?P<scope>)(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>(<)?=)\s*(?P<statement>.*)$')
        txt_new = txt
        max_len_glob = {}
        for re_str in re_str_l:
            lines = txt_new.splitlines()
            lines_match = []
            matched = False
            # Process each line to identify a signal declaration, save the match information in an array, and process the max length for each field
            for l in lines:
                l = l
                m = re.search(re_str,l)
                ilvl = self.getIndentLevel(l)
                len_c = 0
                if m:
                    matched = True
                    len_c = len(m.group('name'))
                    if m.group('scope'):
                        len_c += len(m.group('scope'))
                        if m.group('scope') == 'assign':
                            len_c+=1
                    if m.group('bitslice'):
                        len_c += len(re.sub(r'\s','',m.group('bitslice')))+2
                    if ilvl not in max_len_glob or len_c>max_len_glob[ilvl]:
                        max_len_glob[ilvl] = len_c
                lines_match.append((l,m,ilvl,len_c))
            # If no match return text as is
            if matched :
                txt_new = ''
                ilvl_prev = -1
                # Update alignement of each line
                for idx,(line,m,ilvl,len_c) in enumerate(lines_match):
                    if m:
                        l = ''
                        if m.group('scope'):
                            l += m.group('scope')
                            if m.group('scope') == 'assign':
                                l+=' '
                        l += m.group('name')
                        if m.group('bitslice'):
                            l += '[' + re.sub(r'\s','',m.group('bitslice')) + ']'
                        # l = self.indent*ilvl + l.ljust(max_len) + ' ' + m.group('op') + ' ' + m.group('statement')
                        l = self.indent*ilvl + l.ljust(max_len_glob[ilvl]) + ' ' + m.group('op') + ' ' + m.group('statement')
                        ilvl_prev = ilvl
                    else :
                        l = line
                        ilvl_prev = -1
                    txt_new += l.rstrip() + '\n'
                if txt[-1]!='\n':
                    txt_new = txt_new[:-1]
        return txt_new

    # Alignement for module instance
    def alignInstance(self,txt,ilvl):
        # Check if parameterized module
        m = re.search(r'(?s)(?P<emptyline>\n*)(?P<mtype>^[ \t]*\w+)\s*(?P<paramsfull>#\s*\((?P<params>.*)\s*\))?\s*(?P<mname>\w+)\s*\(\s*(?P<ports>.*)\s*\)\s*;(?P<comment>.*)$',txt,flags=re.MULTILINE)
        if not m:
            return ''
        # Add module type
        txt_new = m.group('emptyline') + self.indent*(ilvl) + m.group('mtype').strip()
        #Add parameter binding : if already on one line simply remove extra space, otherwise apply standard alignement
        if m.group('params'):
            txt_new += ' #('
            if ('\n' in m.group('params').strip()) or not self.settings['paramOneLine']:
                txt_new += '\n'+self.alignInstanceBinding(m.group('params'),ilvl+1)+self.indent*(ilvl)
            else :
                p = m.group('params').strip()
                p = re.sub(r'\s+','',p)
                p = re.sub(r'\),',r'), ',p)
                txt_new += p
            txt_new += ')'
        # Add module name
        txt_new += ' ' + m.group('mname') + ' ('
        # Add ports binding
        if m.group('ports'):
            # if port binding starts with a .* let it on the same line
            if not m.group('ports').startswith('.*') and '\n' in m.group('ports').rstrip():
                txt_new += '\n'
            if '\n' in m.group('ports').strip() :
                txt_new += self.alignInstanceBinding(m.group('ports'),ilvl+1)
                txt_new += self.indent*(ilvl) + ');'
            else:
                p = m.group('ports').strip()
                p = re.sub(r'\s+','',p)
                p = re.sub(r'\),',r'), ',p)
                txt_new += p +');'
        # Add end
        if m.group('comment'):
            txt_new += ' ' + m.group('comment')
        return txt_new

    def alignInstanceBinding(self,txt,ilvl):
        was_split = False
        # insert line if needed to get one binding per line
        if self.settings['oneBindPerLine']:
            txt = re.sub(r'\)[ \t]*,[ \t]*\.', '), \n.', txt,flags=re.MULTILINE)
        # Parse bindings to find length of port and signals
        re_str_bind_port = r'^[ \t]*(?P<lcomma>,)?[ \t]*\.\s*(?P<port>\w+)\s*\(\s*'
        re_str_bind_sig = r'(?P<signal>.*?)\s*\)\s*(?P<comma>,)?\s*(?P<comment>\/\/.*?|\/\*.*?)?$'
        binds = re.findall(re_str_bind_port+re_str_bind_sig,txt,flags=re.MULTILINE)
        max_port_len = 0
        max_sig_len = 0
        ports_len = [len(x[1]) for x in binds]
        sigs_len = [len(x[2].strip()) for x in binds]
        if ports_len:
            max_port_len = max(ports_len)
        if sigs_len:
            max_sig_len = max(sigs_len)
        #TODO: if the .* is at the beginning make sure it is not follow by another binding
        lines = txt.strip().splitlines()
        txt_new = ''
        # for each line apply alignment
        for i,line in enumerate(lines):
            # Remove leading and trailing space. add end of line
            l = line.strip()
            # ignore empty line at the begining and the end of the connection
            if (i!=(len(lines)-1) and i!=0) or l !='':
                # Look for a binding
                m = re.search(r'^'+re_str_bind_port+re_str_bind_sig,l)
                is_split = False
                # No complete binding : look for just the beginning then
                if not m:
                    m = re.search(re_str_bind_port+r'(?P<signal>.*?)\s*(?P<comma>)(?P<comment>)$',l)
                    if m:
                        is_split = True
                        # print('Detected split at Line ' + str(i) + ' : ' + l)
                if m:
                    # print('Line ' + str(i) + '/' + str(len(lines)) + ' : ' + str(m.groups()) + ' => split = ' + str(is_split))
                    txt_new += self.indent*(ilvl)
                    txt_new += '.' + m.group('port').ljust(max_port_len)
                    txt_new += '(' + m.group('signal').strip().ljust(max_sig_len)
                    if not is_split:
                        txt_new += ')'
                        if i!=(len(lines)-1): # Add comma for all lines except last
                            txt_new += ','
                    if m.group('comment'):
                        if txt_new[-1] != ',':
                            txt_new += ' '
                        txt_new += ' ' + m.group('comment')
                else : # No port binding ? recopy line with just the basic indentation level
                    txt_new += self.indent*ilvl
                    # Handle case of binding split on multiple line : try to align the end of the binding
                    if was_split:
                        txt_new += ''.ljust(max_port_len+2) #2 = take into account the . and the (
                        m = re.search(re_str_bind_sig,l)
                        if m:
                            if m.group('signal'):
                                txt_new += m.group('signal').strip().ljust(max_sig_len) + ')'
                            else :
                                txt_new += ''.strip().ljust(max_sig_len) + ')'
                            if m.group('comma') and i!=(len(lines)-1):
                                txt_new += ', '
                            else:
                                txt_new += '  '
                            if m.group('comment'):
                                txt_new += m.group('comment')
                        else :
                            txt_new += l
                    else :
                        txt_new += l
                was_split = is_split
                txt_new += '\n'
        return txt_new

    # Alignement for signal declaration : [scope::]type [signed|unsigned] [bitwidth] signal list
    def alignDecl(self,txt):
        lines = txt.splitlines()
        lines_match = []
        len_max = {}
        one_decl_per_line = self.settings['oneDeclPerLine']
        # Process each line to identify a signal declaration, save the match information in an array, and process the max length for each field
        for l in lines:
            m = self.re_decl.search(l)
            if m:
                ilvl = self.getIndentLevel(l)
                if ilvl not in len_max:
                    len_max[ilvl] = [0,0,0,0,0,0,0,0,0,0]
                for i,g in enumerate(m.groups()):
                    if g:
                        if len(g.strip()) > len_max[ilvl][i]:
                            len_max[ilvl][i] = len(g.strip())
                        if i==8 and one_decl_per_line:
                            for s in g.split(','):
                                if len(s.strip()) > len_max[ilvl][5]:
                                    len_max[ilvl][5] = len(s.strip())
            else:
                ilvl = 0
            lines_match.append((l,m,ilvl))
        # Update alignement of each line
        txt_new = ''
        for line,m,ilvl in lines_match:
            if m:
                l = self.indent*ilvl
                if m.groups()[0]:
                    l += (m.groups()[0]+m.groups()[1]).ljust(len_max[ilvl][0]+len_max[ilvl][1]+1)
                else:
                    l += m.groups()[1].ljust(len_max[ilvl][0]+len_max[ilvl][1]+1)
                #Align with signess only if it exist in at least one of the line
                if len_max[ilvl][2]>0:
                    if m.groups()[2]:
                        l += m.groups()[2].ljust(len_max[ilvl][2]+1)
                    else:
                        l += ''.ljust(len_max[ilvl][2]+1)
                #Align with width only if it exist in at least one of the line
                if len_max[ilvl][4]>1:
                    if m.groups()[4]:
                        l += '[' + m.groups()[4].strip().rjust(len_max[ilvl][4]) + '] '
                    else:
                        l += ''.rjust(len_max[ilvl][4]+3)
                d = l # save signal declaration before signal name in case it needs to be repeated for a signal list
                # list of signals : do not align with the end of lign
                if m.groups()[8]:
                    l += m.groups()[5]
                    if one_decl_per_line:
                        for s in m.groups()[8].split(','):
                            if s != '':
                                l += ';\n' + d + s.strip().ljust(len_max[ilvl][5])
                    else :
                        l += m.groups()[8].strip()
                else :
                    l += m.groups()[5].ljust(len_max[ilvl][5])
                    if len_max[ilvl][6]>1:
                        if m.groups()[7]:
                            l += '[' + m.groups()[7].strip().rjust(len_max[ilvl][7]) + ']'
                        else:
                            l += ''.rjust(len_max[ilvl][7]+2)
                l += ';'
                if m.groups()[9]:
                    l += ' ' + m.groups()[9].strip()
            else : # Not a declaration ? don't touch
                l = line
            txt_new += l + '\n'
        if txt[-1]!='\n':
            txt_new = txt_new[:-1]
        return txt_new


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verilog Beautifier')
    parser.add_argument('-i','--input' , required=True ,                          help='Verilog filename to beautify')
    parser.add_argument('-o','--output', required=False,           default='',    help='Output filename. Default to input filename.')
    parser.add_argument('-t','--tab'   , required=False,           default=False, help='Use tabulation for indentation (default: False')
    parser.add_argument('-s','--space' , required=False, type=int, default=3,     help='Number of space for an indentation level. Default to 3.')
    parser.add_argument('--no-oneBindPerLine', dest='oneBindPerLine', action='store_false', help='Allow more than one port binding per line in instance')
    parser.add_argument('--oneDeclPerLine', dest='oneDeclPerLine', default=False, action='store_true', help='Force only one declration per line.')
    parser.set_defaults(oneBindPerLine=True)
    args = parser.parse_args()
    beautifier = VerilogBeautifier(nbSpace=args.space, useTab=args.tab, oneBindPerLine=args.oneBindPerLine, oneDeclPerLine=args.oneDeclPerLine)
    beautifier.beautifyFile(fnameIn=args.input, fnameOut=args.output)

