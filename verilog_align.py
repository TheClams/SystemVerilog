import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
import verilogutil
import sublimeutil

class VerilogAlign(sublime_plugin.TextCommand):

    def run(self,edit, cmd=""):
        if len(self.view.sel())==0 : return;
        # TODO: handle multi cursor. Currently only first one ise used
        # Expand the selection to a complete scope supported by the one of the align function
        # Get sublime setting
        self.settings = self.view.settings()
        self.tab_size = int(self.settings.get('tab_size', 4))
        self.char_space = ' ' * self.tab_size
        self.use_space = self.settings.get('translate_tabs_to_spaces')
        current_pos = self.view.viewport_position()
        if not self.use_space:
            self.char_space = '\t'
        # region = self.view.extract_scope(self.view.line(self.view.sel()[0]).a)
        region = self.view.sel()[0]
        region_start = region
        scope = self.view.scope_name(region.a)
        txt = ''
        if cmd == 'reindent':
            # Select whole text if nothing is selected
            # Otherwise expand to the line
            if region.empty():
                region = sublime.Region(0,self.view.size())
            else :
                region = self.view.line(self.view.sel()[0])
            txt = self.reindent(self.view.substr(region))
        elif 'meta.module.inst' in scope:
            (txt,region) = self.inst_align(region)
        elif 'meta.module.systemverilog' in scope:
            (txt,region) = self.port_align(region)
        else :
            # empty region ? select all lines before and after until an empty line is found
            if region.empty():
                region = self.view.expand_by_class(region,sublime.CLASS_EMPTY_LINE)
                # TODO: maybe have a better approach stopping at a begin end and line of comment as well
            else:
                region = self.view.line(self.view.sel()[0])
            if self.view.classify(region.b) & sublime.CLASS_EMPTY_LINE :
                region.b -= 1;
            if self.view.classify(region.a) & sublime.CLASS_EMPTY_LINE :
                region.a += 1;
            txt = self.view.substr(region)
            (txt,region) = self.decl_align(txt, region)
            (txt,region) = self.assign_align(txt, region)
        if txt:
            self.view.replace(edit,region,txt)
            sublimeutil.move_cursor(self.view,region_start.a)
        else :
            sublime.status_message('No alignement support for this block of code.')

    def get_indent_level(self,txt):
        # make sure to not have mixed tab/space
        if self.use_space:
            t = txt.replace('\t',self.char_space)
        else:
            t = txt.replace(self.char_space,'\t')
        cnt = (len(t) - len(t.lstrip()))
        if self.use_space:
            cnt = int(cnt/self.tab_size)
        return cnt

    # Alignement for module instance
    def inst_align(self,region):
        r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',region)
        # Make sure to get complete line to be able to get initial indentation
        r = self.view.line(r)
        txt = self.view.substr(r).rstrip()
        # Check if parameterized module
        m = re.search(r'(?s)(?P<mtype>^[ \t]*\w+)\s*(?P<paramsfull>#\s*\((?P<params>.*)\s*\))?\s*(?P<mname>\w+)\s*\(\s*(?P<ports>.*)\s*\)\s*;(?P<comment>.*)$',txt,re.MULTILINE)
        if not m:
            sublime.status_message('Unable to match a module instance !')
            return
        nb_indent = self.get_indent_level(m.group('mtype'))
        # Add module type
        txt_new = self.char_space*(nb_indent) + m.group('mtype').strip()
        #Add parameter binding : if already on one line simply remove extra space, otherwise apply standard alignement
        if m.group('params'):
            txt_new += ' #('
            if '\n' in m.group('params').strip() :
                txt_new += '\n'+self.inst_align_binding(m.group('params'),nb_indent+1)+self.char_space*(nb_indent)
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
            if not m.group('ports').startswith('.*'):
                txt_new += '\n'
            txt_new += self.inst_align_binding(m.group('ports'),nb_indent+1)
        # Add end
        txt_new += self.char_space*(nb_indent) + '); '
        if m.group('comment'):
            txt_new += m.group('comment')
        return (txt_new,r)

    def inst_align_binding(self,txt,nb_indent):
        was_split = False
        # insert line if needed to get one binding per line
        if self.settings.get('sv.one_bind_per_line',True):
            txt = re.sub(r'\)[ \t]*,[ \t]*\.', '), \n.', txt,re.MULTILINE)
        # Parse bindings to find length of port and signals
        re_str_bind_port = r'^[ \t]*(?P<lcomma>,)?[ \t]*\.\s*(?P<port>\w+)\s*\(\s*'
        re_str_bind_sig = r'(?P<signal>.*)\s*\)\s*(?P<comma>,)?\s*(?P<comment>\/\/.*?|\/\*.*?)?$'
        binds = re.findall(re_str_bind_port+re_str_bind_sig,txt,re.MULTILINE)
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
                    txt_new += self.char_space*(nb_indent)
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
                    txt_new += self.char_space*nb_indent
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

    # Alignement for port declaration (for ansi-style)
    def port_align(self,region):
        r = sublimeutil.expand_to_scope(self.view,'meta.module.systemverilog',region)
        txt = self.view.substr(r)
        # Extract parameter and ports
        m = re.search(r'(?s)(?P<module>^[ \t]*module)\s*(?P<mname>\w+)\s*(?P<paramsfull>#\s*\(\s*parameter\s+(?P<params>.*)\s*\))?\s*\(\s*(?P<ports>.*)\s*\)\s*;$',txt,re.MULTILINE)
        if not m:
            sublime.status_message('Unable to match a module declaration !')
            return ('',r)
        # Add module declaration
        nb_indent = self.get_indent_level(m.group('module'))
        txt_new = self.char_space*(nb_indent) + 'module ' + m.group('mname').strip()
        # Add optional parameter declaration
        if m.group('params'):
            m.group('params').strip()
            param_txt = re.sub(r'(^|,)\s*parameter','',m.group('params').strip()) # remove multiple parameter declaration
            re_str = r'^[ \t]*(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<param>\w+)\b\s*=\s*(?P<value>[\w\:`]+)\s*(?P<sep>,)?[ \t]*(?P<list>\w+\s*=\s*\w+(,)?\s*)*(?P<comment>.*?$)'
            decl = re.findall(re_str,param_txt,re.MULTILINE)
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
                    txt_new += self.char_space*(nb_indent+1)
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
                    txt_new += '\n' + self.char_space*(nb_indent)
            else :
                txt_new += ' ' + param_txt
                # print('len Comment = ' + str(len_comment)+ ': ' + str([x[9] for x in decl])+ '"')
                if len_comment > 0 :
                    txt_new += '\n' + self.char_space*(nb_indent)
            txt_new += ')'
            #
        # Add port list declaration
        txt_new += ' (\n'
        # Port declaration: direction type? signess? buswidth? list ,? comment?
        re_str = r'^[ \t]*(?P<dir>[\w\.]+)[ \t]+(?P<var>var\b)?[ \t]*(?P<type>[\w\:]+\b)?[ \t]*(?P<sign>signed|unsigned\b)?[ \t]*(\[(?P<bw>[\w\:\-` \t]+)\])?[ \t]*(?P<ports>(?P<port1>\w+)[\w, \t]*)[ \t]*(?P<comment>.*)'
        decl = re.findall(re_str,m.group('ports'),re.MULTILINE)
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
                txt_new += self.char_space*(nb_indent+1)
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
                    txt_new += l
                # Remove trailing spaces/tabs and add the end of line
                txt_new = txt_new.rstrip(' \t') + '\n'
        txt_new += self.char_space*(nb_indent) + ');'
        return (txt_new,r)


    # Alignement for signal declaration : [scope::]type [signed|unsigned] [bitwidth] signal list
    def decl_align(self,txt, region):
        lines = txt.splitlines()
        #TODO handle array
        re_str = r'^[ \t]*(\w+\:\:)?(\w+)[ \t]+(signed|unsigned\b)?[ \t]*(\[([\w\:\-` \t]+)\])?[ \t]*([\w\[\]]+)[ \t]*(,[\w, \t]*)?;[ \t]*(.*)'
        lines_match = []
        len_max = [0,0,0,0,0,0,0,0]
        nb_indent = -1
        one_decl_per_line = self.settings.get('sv.one_decl_per_line',False)
        # Process each line to identify a signal declaration, save the match information in an array, and process the max length for each field
        for l in lines:
            m = re.search(re_str,l)
            lines_match.append(m)
            if m:
                if nb_indent < 0:
                    nb_indent = self.get_indent_level(l)
                for i,g in enumerate(m.groups()):
                    if g:
                        if len(g.strip()) > len_max[i]:
                            len_max[i] = len(g.strip())
                        if i==6 and one_decl_per_line:
                            for s in g.split(','):
                                if len(s.strip()) > len_max[5]:
                                    len_max[5] = len(s.strip())
        # Update alignement of each line
        txt_new = ''
        for line,m in zip(lines,lines_match):
            if m:
                l = self.char_space*nb_indent
                if m.groups()[0]:
                    l += m.groups()[0]
                l += m.groups()[1].ljust(len_max[0]+len_max[1]+1)
                #Align with signess only if it exist in at least one of the line
                if len_max[2]>0:
                    if m.groups()[2]:
                        l += m.groups()[2].ljust(len_max[2]+1)
                    else:
                        l += ''.ljust(len_max[2]+1)
                #Align with signess only if it exist in at least one of the line
                if len_max[4]>1:
                    if m.groups()[4]:
                        l += '[' + m.groups()[4].strip().rjust(len_max[4]) + '] '
                    else:
                        l += ''.rjust(len_max[4]+3)
                d = l # save signal declaration before signal name in case it needs to be repeated for a signal list
                # list of signals : do not align with the end of lign
                if m.groups()[6]:
                    l += m.groups()[5]
                    if one_decl_per_line:
                        for s in m.groups()[6].split(','):
                            if s != '':
                                l += ';\n' + d + s.strip().ljust(len_max[5])
                    else :
                        l += m.groups()[6].strip()
                else :
                    l += m.groups()[5].ljust(len_max[5])
                l += ';'
                if m.groups()[7]:
                    l += ' ' + m.groups()[7].strip()
            else : # Not a declaration ? don't touch
                l = line
            txt_new += l + '\n'
        return (txt_new[:-1],region)

    # Alignement for case/structure assign : "word: statement"
    def assign_align(self,txt, region):
        #TODO handle array
        re_str_l = []
        re_str_l.append(r'^[ \t]*(?P<scope>\w+\:\:)?(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>\:)\s*(?P<statement>.*)$')
        re_str_l.append(r'^[ \t]*(?P<scope>assign)\s+(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>=)\s*(?P<statement>.*)$')
        re_str_l.append(r'^[ \t]*(?P<scope>)(?P<name>[\w`\'\"\.]+)[ \t]*(\[(?P<bitslice>.*?)\])?\s*(?P<op>(<)?=)\s*(?P<statement>.*)$')
        txt_new = txt
        for re_str in re_str_l:
            lines = txt_new.splitlines()
            lines_match = []
            nb_indent = -1
            max_len = 0
            # Process each line to identify a signal declaration, save the match information in an array, and process the max length for each field
            for l in lines:
                m = re.search(re_str,l)
                lines_match.append(m)
                if m:
                    if nb_indent < 0:
                        nb_indent = self.get_indent_level(l)
                    len_c = len(m.group('name'))
                    if m.group('scope'):
                        len_c += len(m.group('scope'))
                        if m.group('scope') == 'assign':
                            len_c+=1
                    if m.group('bitslice'):
                        len_c += len(re.sub(r'\s','',m.group('bitslice')))+2
                    if len_c > max_len:
                        max_len = len_c
            # If no match return text as is
            if max_len!=0 :
                txt_new = ''
                # Update alignement of each line
                for line,m in zip(lines,lines_match):
                    if m:
                        l = ''
                        if m.group('scope'):
                            l += m.group('scope')
                            if m.group('scope') == 'assign':
                                l+=' '
                        l += m.group('name')
                        if m.group('bitslice'):
                            l += '[' + re.sub(r'\s','',m.group('bitslice')) + ']'
                        l = self.char_space*nb_indent + l.ljust(max_len) + ' ' + m.group('op') + ' ' + m.group('statement')
                    else :
                        l = line
                    txt_new += l + '\n'
                txt_new = txt_new[:-1]

        return (txt_new,region)

    # Parse text and apply proper indentation
    def reindent(self, txt):
        words = re.findall(r"\w+|[^\w\s]|[ \t]+|\n", txt, re.MULTILINE)
        incr_w_now = ['begin', 'case']
        incr_w = ['module', 'class', 'interface','function','task', 'package']
        incr_next = False
        decr_w = ['end', 'endmodule', 'endclass', 'endinterface', 'endfunction', 'endtask', 'endcase', 'endpackage']
        nb_indent = self.get_indent_level(txt)
        txt_new = ''
        last_token = '\n'
        last_w = ''
        line = ''
        next_token = ''
        cnt_brace = 0
        is_split = 0
        is_block_indent = [] # list of block level at which a block indent has been found (GNU style begin/end or {})
        is_block_decl = False # 1 when inside a block declaration like struct {} or constraint {}
        cnt_line = 0
        has_decr = False
        for w in words:
            if w == '\n':
                cnt_line +=1
                last_w = ''
            # Inside a single line comment ? simply copy until the end of line
            if last_token=='//':
                if w!='\n':
                    txt_new += w
                    continue
            # Inside a multiline comment ? simply copy until the */
            if last_token=='/*':
                txt_new += w
                if last_w=='*' and w=='/':
                    last_token=''
                last_w = w
                continue
            # Check for decrease indent word
            if w in decr_w or ( w == '}' and is_block_decl):
                if nb_indent >0: # Should never happen ...
                    nb_indent -= 1
                has_decr = True
                # print('[Reindent Line %d] Decr indent level to %d due to token %s' %(cnt_line,nb_indent,w)) ##DEBUG
            # Check for declaration block for struct, union, constraint, ...
            if w in ['struct', 'union', 'constraint']:
                is_block_decl = True
            elif w == '}' and cnt_brace==1:
                is_block_decl = False
            # Insert indentation
            if last_token=='\n':
                if not w.strip():
                    if w == '\n':
                        txt_new += w
                        last_w = ''
                    else :
                        last_w = w
                    continue
                if w in [')', '}']:
                    # print('[Reindent Line %d] Reseting is_split after %s'%(cnt_line,w)) ##DEBUG
                    is_split = 0
                if w != '/' or is_split!=0:
                    txt_new += self.char_space*(nb_indent+is_split+len(is_block_indent))
                else :
                    txt_new += last_w
                    # print('[Reindent Line %d] Comment line, keep indentation "%s"'%(cnt_line,last_w)) ##DEBUG
            if w in ['end', '}'] and is_block_indent and is_block_indent[-1]==cnt_brace:
                is_block_indent.pop()
                # print('[Reindent Line %d] pop is_block_indent=%s  afer token %s' %(cnt_line,is_block_indent,w)) ##DEBUG
            # Check for increase indent word
            if w in incr_w_now:
                # print('[Reindent Line %d] Incr indent level to %d due to token %s.' %(cnt_line,nb_indent,w)) ##DEBUG
                nb_indent += 1
            elif w == '{' and is_block_decl:
                # print('[Reindent Line %d] Incr indent level to %d due to token %s (is_block_decl).' %(cnt_line,nb_indent,w)) ##DEBUG
                nb_indent += 1
            elif w in incr_w:
                if not line.strip().startswith('import'):
                    # print('[Reindent Line %d] Incr indent will be increase on next ; due to token %s' %(cnt_line,w)) ##DEBUG
                    incr_next = True
            if w == '{':
                cnt_brace += 1
            elif w == '}':
                cnt_brace -= 1
            if w=='\n' and line.strip():
                m = re.search(r'(;|{)\s*$|(begin(\s*\:\s*\w+)?)$|(case)\s*\(.*\)\s*$|(`\w+)\s*(\(.*\))?\s*$|^\s*(`\w+)\s*',line)
                m_str = 'None'
                if line.strip() in ['begin','{'] :
                    is_block_indent.append(cnt_brace)
                    # print('[Reindent Line %d] block_indent=%s due to line %s. ' %(cnt_line,is_block_indent,line)) ##DEBUG
                if m:
                    m_str = str(m.groups())
                if line.strip().endswith('{') and not is_block_decl:
                    is_split = 1
                    # print('[Reindent Line %d] is_split due to {' %(cnt_line)) ##DEBUG
                elif not m and last_token not in decr_w and not has_decr:
                    is_split = 1
                    # print('[Reindent Line %d] is_split. m=%s, last_token=%s, line="%s"' %(cnt_line,m_str,last_token,line.strip())) ##DEBUG
                else :
                    # print('[Reindent Line %d] End of line, no is_split: m=%s, last_token=%s, line="%s"' %(cnt_line,m_str,last_token,line.strip())) ##DEBUG
                    is_split = 0
                    if incr_next and m and m.groups()[0]==';':
                        incr_next = False
                        nb_indent += 1
                        # print('[Reindent Line %d] Incr indent level to %d due to previous incr_next' %(cnt_line,nb_indent)) ##DEBUG
                line = ''
                has_decr = False
            else :
                line += w
            # Add word to the new text
            txt_new += w
            # Concat word for token
            if last_token =='/':
                last_token += w
                if last_token in ['/*','//']  :
                    line = line[:-2]
            else :
                last_token = w
        return txt_new
