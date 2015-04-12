import argparse
import re
import string
import verilogutil

class VerilogBeautifier():

    def __init__(self, nbSpace=3, useTab=False, oneBindPerLine=True, oneDeclPerLine=False):
        self.settings = {'nbSpace': nbSpace, 'useTab':useTab, 'oneBindPerLine':oneBindPerLine, 'oneDeclPerLine':oneDeclPerLine}
        self.indentSpace = ' ' * nbSpace
        if useTab:
            self.indent = '\t'
        else:
            self.indent = self.indentSpace
        self.states = []
        self.state = ''
        self.re_decl = re.compile(r'^[ \t]*(\w+\:\:)?([A-Za-z_]\w*)[ \t]+(signed|unsigned\b)?[ \t]*(\[([\w\:\-\+></` \t]+)\])?[ \t]*([A-Za-z_][\w\[\]]*)[ \t]*(\[([\w\:\-\+></\$` \t]+)\])?[ \t]*(,[\w, \t]*)?;[ \t]*(.*)')

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
        return (self.state=='begin' and w=='end') or (self.state=='{' and w=='}') or (self.state=='(' and w==')') or (self.state and w=='end' + self.state)

    def beautifyFile(self,fnameIn,fnameOut=''):
        if not fnameOut:
            fnameOut = fnameIn
        with open(fnameIn, "r") as f:
            txt = f.read()
        txt = self.beautifyText(txt)
        with open(fnameOut, "w") as f:
            f.write(txt)

    def beautifyText(self,txt):
        kw_block = ['module', 'class', 'interface', 'program', 'function', 'task', 'package', 'case', 'generate', 'begin', '{', '(']
        # Variables
        self.states = [] # block indent list
        w_d = ['','\n'] # previous word
        line = '' # current line
        block = '' # block of text to align
        block_state = ''
        block_handled = False
        txt_new = '' # complete text beautified
        ilvl = self.getIndentLevel(txt)
        ilvl_prev = ilvl
        has_indent = ilvl!=0
        line_cnt = 1
        split_cnt = 0
        split_always = 0
        split_assign = 0
        always_state = ''
        # Split all text in word, special character, space and line return
        words = re.findall(r"\w+|[^\w\s]|[ \t]+|\n", txt, flags=re.MULTILINE)
        for w in words:
            # print('[Beautify] state={state:<16} -- ilvl={ilvl} -- {line_cnt:4}: "{word}" => "{line}"'.format(line_cnt=line_cnt, word=w, state=self.state, ilvl=ilvl, line=block))
            state_end = self.isStateEnd(w)
            # Start of line ?
            if w_d[-1]=='\n':
                ilvl_prev = ilvl
                if not w.strip():
                    if w!='\n' and block_state in ['module']:
                        block+=w
                    has_indent = w!='\n'
                if state_end:
                    self.stateUpdate()
                    assert ilvl>0, '[Beautify] Block end with already no indentation ! Line {line_cnt:4}: "{line:<150}" => state={state:<16} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state)
                    ilvl-=1
                # Handle end of block_state
                if block_state=='assign' and w!='assign' and not re.match(r'[\t ]+',w):
                    txt_new += self.alignAssign(block,2)
                    block = ''
                    block_state = ''
                # Insert indentation except for comment_block without initial indentation and module declaration
                if block_state not in ['module'] and (self.state!='comment_block' or has_indent) and w.strip():
                    ilvl_tmp = ilvl+split_cnt
                    if self.state!='(' : # TODO: align on ( position in some case ?
                        ilvl_tmp += split_always
                        ilvl_tmp += split_assign # todo align on = position in some case ?
                    line = ilvl_tmp * self.indent
            if w=='\n':
                if split_assign==0 and self.state not in ['comment_block','{'] and block_state not in ['module','instance','struct']:
                    if self.state == 'comment_line' and len(self.states)>1 and self.states[-2] == '{':
                        print('Inside a block {} => ignore for split !')
                        tmp = None
                    else :
                        tmp = verilogutil.clean_comment(line).strip()
                    if tmp:
                        m = re.search(r'(;|\{|\bend)$|(begin(\s*\:\s*\w+)?)$|(case)\s*\(.*\)$|(`\w+)\s*(\(.*\))?$|^(`\w+)\b',tmp)
                        if not m:
                            if tmp.startswith('always'):
                                split_always = 1
                                # print('[Beautify] Split always on line {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=block_state, ilvl=ilvl))
                            elif ilvl==ilvl_prev :
                                m = re.match(r'^\s*(assign\s+)?\w+\s*(<?=)\s*(.*)',tmp)
                                if m:
                                    split_assign = 1
                                    # print('[Beautify] Split assign on line {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=block_state, ilvl=ilvl))
                                else :
                                    split_cnt +=1
                                    # print('[Beautify] Split on line {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.states, block_state=block_state, ilvl=ilvl))
                if block_state == 'decl' and not self.re_decl.match(line):
                    txt_new += self.alignDecl(block)
                    block = ''
                    block_state = ''
                # print('[Beautify] {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=block_state, ilvl=ilvl))
                block += line.rstrip() + '\n'
                line = ''
                line_cnt+=1
            # else:
            elif not w_d[-1]=='\n' or w.strip():
                line += w
                if self.state not in ['comment_line','comment_block']:
                    if w in kw_block:
                        ilvl+=1
                        self.stateUpdate(w)
                        if w in ['module','package']:
                            block_state = w
                            txt_new += block
                            block = line
                            line = ''
                    # Identify block_state
                    elif not block_state:
                        if w in ['assign']:
                            block_state = w
                        elif w.startswith('always'):
                            block_state = 'always'
                            always_state = ''
                            # print('Start of always block')
                        elif w_d[-1]=='\n' and w!= '/' and not state_end:
                            # print('Start of text block with "{0}"'.format(w))
                            block_state = 'text'
                    elif block_state=='text':
                        # print('Testing {0}'.format(block+line))
                        tmp = verilogutil.clean_comment(block + line).strip()
                        m = re.match(r'(?s)^\s*\b(?P<itype>\w+)\s*(#\s*\([^;]+\))?\s*\b(?P<iname>\w+)\s*\(',tmp, flags=re.MULTILINE)
                        if m and m.group('itype') not in ['else', 'begin', 'end'] and m.group('iname') not in ['if','for','foreach']:
                            block_state = 'instance'
                        elif re.match(r'\s*\b(typedef\s+)?(struct|union)\b',tmp, flags=re.MULTILINE):
                            block_state = 'struct'
                        elif re.match(r"(?s)^.*=\s*'\{",tmp, flags=re.MULTILINE):
                            # print('Matching strict assign on "{0}"'.format(block+line))
                            block_state = 'struct_assign'
                        # print('Test "{0}" => {1}.{2}'.format((block+line).strip(),self.state,block_state))
            # Handle the block_state and call appropriate alignement function
            if w==';' and self.state not in ['comment_line','comment_block']:
                split_assign = 0;
                if block_state in ['text','decl'] and self.re_decl.match(line):
                    block_state = 'decl'
                    # print('Setting Block state to decl')
                elif block_state in ['module','instance','text','package','decl'] or (block_state in ['struct','struct_assign'] and self.state!='{'):
                    # print('Aligning block {0}'.format(block_state))
                    if block_state=='module':
                        block_tmp = self.alignModulePort(block+line,ilvl-1)
                        line = ''
                    elif block_state=='instance':
                        block_tmp = self.alignInstance(block+line,ilvl)
                        line = ''
                    elif block_state=='struct':
                        block_tmp = self.alignDecl(block+line)
                        line = ''
                    elif block_state=='struct_assign':
                        block_tmp = self.alignAssign(block+line,1)
                        line = ''
                    elif block_state=='decl':
                        block_tmp = self.alignDecl(block)
                    else:
                        block_tmp = block + line
                        line = ''
                    if not block_tmp:
                        print('[Beautify: ERROR] Unable to extract a {0} from "{1}"'.format(block_state,block))
                    else:
                        block = block_tmp
                    block_state = ''
                    block_handled = True
            # Handle end of split
            if split_cnt>0:
                if self.state not in ['comment_line','comment_block'] and w==';' :
                    # print('[Beautify] End Split on line {line_cnt:4}: "{line:<140}" => state={block_state}.{state} -- ilvl={ilvl}'.format(line_cnt=line_cnt, line=line, state=self.state, block_state=block_state, ilvl=ilvl))
                    split_cnt = 0
            # Handle the end of self.state
            if state_end:
                # Check if this was not already handled
                if w_d[-1]!='\n':
                    self.stateUpdate()
                    assert ilvl>0, '[Beautify] Block end with already no indentation ! Line {line_cnt:4}: "{line:<150}" => state={state:<16} '.format(line_cnt=line_cnt, line=line, state=self.state)
                    ilvl-=1
            # Comment: do not try to recognise words, just end of the comment
            elif self.state=='comment_line':
                if w=='\n':
                    self.stateUpdate()
                    if not block_state:
                        block_handled = True
            elif self.state=='comment_block':
                if w_d[-1]=='*' and w=='/':
                    self.stateUpdate()
                    block += line
                    line = ''
                    if not block_state:
                        block_handled = True
            #
            else :
                if w_d[-1]=='/':
                    if w=='/':
                        self.stateUpdate('comment_line')
                    elif w=='*':
                        self.stateUpdate('comment_block')
                    if line.strip() in ["//", "/*"] and not has_indent:
                        line = line.strip()
                    # print('[Beautify] state={block_state:<16}.{state:<16} -- ilvl={ilvl} -- {line_cnt:4}: "{line}" '.format(line_cnt=line_cnt, line=line, state=self.state, block_state=block_state, ilvl=ilvl))
            if block_state == 'always' and (not self.state or self.state in ['module','interface']):
                tmp = verilogutil.clean_comment(block + line).strip()
                m = re.match(r'(?s)^\s*always\w*\s+(@\s*(\*|\([^\)]*\)))?\s*begin',tmp, flags=re.MULTILINE)
                if (m and w=='end') or (always_state in ['else',''] and w in ['end',';']):
                    block = self.alignAssign(block+line,7)
                    line = ''
                    block_handled = True
                    always_state = ''
                    split_always = 0
                    # print('[Beautify] End of always block at line {0}: \n{1}'.format(line_cnt,block))
                elif not m :
                    if w == 'else':
                        # print('[Beautify] Inside else part of always at line {0}'.format(line_cnt))
                        always_state = 'else'
                    # handle case of always if() ...; without else
                    elif always_state == 'expect_else' and w.strip() and w != '/':
                        block = (block + line)
                        last_sc = block.rfind(';') + 1
                        last_end = block.rfind('end') + 3
                        if last_end < last_sc:
                            last_end = last_sc
                        line = block[last_end:]
                        block = block[:last_end]
                        # remove extra indent when the always end block is discovered too late
                        if split_always == 1:
                            line = re.sub(r'^'+self.indentSpace,'',line,flags=re.MULTILINE)
                            # print('[Beautify] End of always block at line {0}, extracting {1}'.format(line_cnt,line))
                        block = self.alignAssign(block,7)
                        # print('[Beautify] End of always block at line {0} with word {1}: \n{2}'.format(line_cnt,w,block))
                        if not w.startswith('always'):
                            always_state = ''
                        txt_new += block
                        block = ''
                        split_always = 0
                    elif w == 'if':
                        always_state = 'if'
                        # print('[Beautify] Inside if part of always at line {0}'.format(line_cnt))
                    elif always_state == 'if' and w in ['end',';']:
                        # print('[Beautify] End of if part=> next word has to be an else'.format(line_cnt))
                        always_state = 'expect_else'
            # Add block to the text
            if block_handled:
                # print('[Beautify] state={block_state}.{state} Block handled:\n"{block}" '.format(state=self.state, block_state=block_state, block=block))
                txt_new += block
                block = ''
                block_state = ''
                block_handled = False
            # Keep previous words
            if w.strip() or w_d[-1]!='\n':
                w_d[-2] = w_d[-1]
                w_d[-1] = w
        # Check that there is no reminding stuff todo:
        block = block+line
        if block_state in ['module','instance','text','package','decl'] or (block_state in ['struct','struct_assign'] and self.state!='{'):
            if block_state=='module':
                block_tmp = self.alignModulePort(block,ilvl-1)
            elif block_state=='instance':
                block_tmp = self.alignInstance(block,ilvl)
            elif block_state=='struct':
                block_tmp = self.alignDecl(block)
            elif block_state=='struct_assign':
                block_tmp = self.alignAssign(block,1)
            elif block_state=='decl':
                block_tmp = self.alignDecl(block)
            else:
                block_tmp = block
            if not block_tmp:
                print('[Beautify: ERROR] Unable to extract a {0} from "{1}"'.format(block_state,block))
            else:
                block = block_tmp
        txt_new += block
        return txt_new

    # Align ANSI style port declaration of a module
    def alignModulePort(self,txt, ilvl):
        # Extract parameter and ports
        m = re.search(r'(?s)(?P<module>^[ \t]*module)\s*(?P<mname>\w+)\s*(?P<paramsfull>#\s*\(\s*parameter\s+(?P<params>.*)\s*\))?\s*\(\s*(?P<ports>.*)\s*\)\s*;$',txt,flags=re.MULTILINE)
        if not m:
            return ''
        txt_new = self.indent*(ilvl) + 'module ' + m.group('mname').strip()
        # Add optional parameter declaration
        if m.group('params'):
            m.group('params').strip()
            param_txt = re.sub(r'(^|,)\s*parameter','',m.group('params').strip()) # remove multiple parameter declaration
            re_str = r'^[ \t]*(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<param>\w+)\b\s*=\s*(?P<value>[\w\:`]+)\s*(?P<sep>,)?[ \t]*(?P<list>\w+\s*=\s*\w+(,)?\s*)*(?P<comment>.*?$)'
            decl = re.findall(re_str,param_txt,flags=re.MULTILINE)
            len_type  = max([len(x[0]) for x in decl if x not in ['signed','unsigned']])
            len_sign  = max([len(x[1]) for x in decl])
            len_bw    = max([len(x[3]) for x in decl])
            len_param = max([len(x[4]) for x in decl])
            len_value = max([len(x[5]) for x in decl])
            len_comment = max([len(x[9]) for x in decl])
            # print(str((len_type,len_sign,len_bw,len_param,len_value,len_comment)))
            txt_new += ' #(parameter'
            # If not on one line align parameter together, otherwise keep as is
            if '\n' in param_txt:
                txt_new += '\n'
                lines = param_txt.splitlines()
                for i,line in enumerate(lines):
                    txt_new += self.indent*(ilvl+1)
                    m_param = re.search(re_str,line.strip())
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
                    if m_param.group('sep') and i!=(len(lines)-1):
                        txt_new += m_param.group('sep') + ' '
                    else:
                        txt_new += '  '
                    #TODO: in case of list try to do something: option to split line by line? align in column if multiple list present ?
                    if m_param.group('list'):
                        txt_new += m_param.group('list') + ' '
                    if m_param.group('comment'):
                        txt_new += m_param.group('comment') + ' '
                    txt_new += '\n' + self.indent*(ilvl)
            else :
                txt_new += ' ' + param_txt
                # print('len Comment = ' + str(len_comment)+ ': ' + str([x[9] for x in decl])+ '"')
                if len_comment > 0 :
                    txt_new += '\n' + self.indent*(ilvl)
            txt_new += ')'
            #
        # Add port list declaration
        txt_new += ' (\n'
        # Port declaration: direction type? signess? buswidth? list ,? comment?
        re_str = r'^[ \t]*(?P<dir>[\w\.]+)[ \t]+(?P<var>var\b)?[ \t]*(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<ports>(?P<port1>\w+)[\w, \t]*)[ \t]*(?P<comment>.*)'
        decl = re.findall(re_str,m.group('ports'),flags=re.MULTILINE)
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
        lines = m.group('ports').splitlines()

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
                        else :
                            txt_new += ' '.ljust(len_type_user+1)
                    # For interface
                    else :
                        txt_new += m_port.group('dir').ljust(len_if)
                    # Add port list: space every port in the list by just on space
                    s = re.sub(r',',', ',re.sub(r'\s*','',m_port.group('ports')))
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
            if '\n' in m.group('params').strip() :
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
                txt_new += self.indent*(ilvl) + '); '
            else:
                p = m.group('ports').strip()
                p = re.sub(r'\s+','',p)
                p = re.sub(r'\),',r'), ',p)
                txt_new += p +'); '
        # Add end
        if m.group('comment'):
            txt_new += m.group('comment')
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
                            txt_new += ', '
                        else:
                            txt_new += '  '
                    if m.group('comment'):
                        txt_new += m.group('comment')
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
                            l += '[' + m.groups()[7].strip().rjust(len_max[ilvl][7]) + '] '
                        else:
                            l += ''.rjust(len_max[ilvl][7]+3)
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

