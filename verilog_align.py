import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
import verilogutil
import sublimeutil

class VerilogAlign(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())!=1 : return; # No multi-selection allowed (yet?)
        # Expand the selection to a complete scope supported by the one of the align function
        # Get sublime setting
        self.settings = self.view.settings()
        self.tab_size = int(self.settings.get('tab_size', 4))
        self.char_space = ' ' * self.tab_size
        self.use_space = self.settings.get('translate_tabs_to_spaces')
        if not self.use_space:
            self.char_space = '\t'
        region = self.view.extract_scope(self.view.sel()[0].a)
        scope = self.view.scope_name(region.a)
        txt = ''
        if 'meta.module.inst' in scope:
            (txt,region) = self.inst_align(region)
        elif 'meta.module.systemverilog' in scope:
            (txt,region) = self.port_align(region)
        else :
            region = self.view.line(self.view.sel()[0])
            if self.view.classify(region.b) & sublime.CLASS_EMPTY_LINE :
                region.b -= 1;
            txt = self.view.substr(region)
            (txt,region) = self.decl_align(txt, region)
        if txt != '':
            self.view.replace(edit,region,txt)
        else :
            print ('No alignement support for this block of code.')

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
        # insert line if needed o get one binding per line
        if self.settings.get('sv.one_bind_per_line',True):
            txt = re.sub(r'\)[ \t]*,[ \t]*\.', '), \n.', txt,re.MULTILINE)
        # Realign text
        re_str = r'\.\s*(\w+)\s*\(\s*([\w\[\]\:~`\+-\{\}\s\'&|]*)\s*\)[\s]*'
        bind = re.findall(re_str,txt,re.MULTILINE)
        if len(bind) > 0:
            len_port    = max([len(x[0]) for x in bind])
            len_signals = max([len(x[1].rstrip()) for x in bind])
        else:
            len_port = 0
            len_signals = 0
        txt_new = ''
        lines = txt.splitlines()
        nb_indent = self.get_indent_level(lines[0])
        for i,line in enumerate(lines):
            # Remove leading and trailing space. add end of line
            l = line.lstrip().rstrip()
            line_handled = False
            #Special case of first line: potentially insert an end of line between instance name and port name
            if i==0:
                txt_new += self.char_space*nb_indent
                m = re.search(r'(.*?)(\..*)',l)
                if m:
                    # Let the .* at the beginning
                    if m.groups()[1].startswith('.*') :
                        txt_new += l + '\n'
                        line_handled = True
                    else :
                        txt_new += m.groups()[0] + '\n'
                        l = m.groups()[1]+'\n'
                else :
                    txt_new += l + '\n'
                    line_handled = True
            if not line_handled :
                # Look for a binding (not supporting binding on multiple line : alignement ignored in this case)
                m = re.search(r'^'+re_str+r'(,|\))?\s*(.*)',l)
                if m:
                    # print('Line ' + str(i) + ' : ' + str(m.groups()))
                    if i == len(lines)-1 and m.groups()[2]!=')':
                        txt_new += self.char_space*(nb_indent)
                    else:
                        txt_new += self.char_space*(nb_indent+1)
                    txt_new += '.' + m.groups()[0].ljust(len_port)
                    txt_new += '(' + m.groups()[1].rstrip().ljust(len_signals) + ')'
                    if m.groups()[2]==')' :
                        txt_new += '\n' + self.char_space*nb_indent + ')'
                    elif m.groups()[2]:
                        txt_new += m.groups()[2] + ' '
                    else:
                        txt_new += '  '
                    if m.groups()[3]:
                        txt_new += m.groups()[3]
                    if i != len(lines)-1:
                        txt_new += '\n'
                else : # No port binding ? recopy line with just the basic indentation level
                    if i == len(lines)-1:
                        # handle case where alignement is not supported but there is test with ); on same line: insert return line
                        m = re.search(r'\s*(.+)\s*\)\s*;(.*)',l)
                        if m:
                            txt_new += self.char_space*(nb_indent+1)+m.groups()[0]+'\n'
                            txt_new += self.char_space*(nb_indent)+');' + m.groups()[1]
                        else :
                            txt_new += self.char_space*(nb_indent)+l
                    else:
                        txt_new += self.char_space*(nb_indent+1)+l + '\n'
        return (txt_new,r)

    # Alignement for port declaration (for ansi-style)
    def port_align(self,region):
        r = sublimeutil.expand_to_scope(self.view,'meta.module.systemverilog',region)
        r = self.view.expand_by_class(r,sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
        txt = self.view.substr(r)
        #TODO: handle interface
        # Port declaration: direction type? signess? buswidth? portlist ,? comment?
        re_str = r'^[ \t]*([\w\.]+)[ \t]+(\w+\b)?[ \t]*(\w+\b)?[ \t]*(\[([\w\:\-` \t]+)\])?[ \t]*(\w+[\w, \t]*)'
        decl = re.findall(re_str,txt,re.MULTILINE)
        # if decl:
        #     print(decl)
        # Extract max length of the different field for vertical alignement
        len_dir  = max([len(x[0]) for x in decl if x!='module'])
        len_type = max([len(x[1]) for x in decl if x!='module' and x[1] not in ['signed','unsigned']])
        len_bw   = max([len(re.sub(r'\s*','',x[4])) for x in decl if x!='module'])
        len_port = max([len(re.sub(r',',', ',re.sub(r'\s*','',x[5])))-2 for x in decl if x!='module'])
        len_sign = 0
        for x in decl:
            if x[1] in ['signed','unsigned'] and len_sign<len(x[1]):
                len_sign = len(x[1])
            elif x[2] in ['signed','unsigned'] and len_sign<len(x[2]):
                len_sign = len(x[2])
        # Rewrite block line by line with padding for alignment
        txt_new = ''
        lines = txt.splitlines()
        nb_indent = self.get_indent_level(lines[0])
        for i,line in enumerate(lines):
            # Remove leading and trailing space. add end of line
            l = line.strip()
            #Special case of first line: potentially insert an end of line between instance name and port name
            if i==0 or (i==1 and lines[0]==''):
                txt_new += self.char_space*nb_indent+l + '\n'
            else :
                if i == len(lines)-1:
                    txt_new += self.char_space*(nb_indent)
                else:
                    txt_new += self.char_space*(nb_indent+1)
                m = re.search(re_str+r'(\)\s+;)?\s*(.*)',l)
                if m:
                    # print('Line ' + str(i) + ' : ' + str(m.groups()))
                    # Add direction
                    txt_new += m.groups()[0].ljust(len_dir)
                    # add type space it exists at least for one port
                    if len_type>0:
                        if m.groups()[1]:
                            if m.groups()[1] not in ['signed','unsigned']:
                                txt_new += ' ' + m.groups()[1].ljust(len_type)
                            else:
                                txt_new += ''.ljust(len_type+1) + ' ' + m.groups()[1].ljust(len_sign)
                        else:
                            txt_new += ''.ljust(len_type+1)
                        # add sign space it exists at least for one port
                        if len_sign>0:
                            if m.groups()[2]:
                                txt_new += ' ' + m.groups()[2].ljust(len_sign)
                            elif m.groups()[1] not in ['signed','unsigned']:
                                txt_new += ''.ljust(len_sign+1)
                    elif len_sign>0:
                        if m.groups()[1] in ['signed','unsigned']:
                            txt_new += ' ' + m.groups()[1].ljust(len_sign)
                        elif m.groups()[2]:
                            txt_new += ' ' + m.groups()[2].ljust(len_sign)
                        else:
                            txt_new += ''.ljust(len_sign+1)
                    # Add bus width if it exists at least for one port
                    if len_bw>1:
                        if m.groups()[4]:
                            txt_new += ' [' + m.groups()[4].strip().rjust(len_bw) + ']'
                        else:
                            txt_new += ''.rjust(len_bw+3)
                    # Add port list: space every port in the list by just on space
                    s = re.sub(r',',', ',re.sub(r'\s*','',m.groups()[5]))
                    txt_new += ' '
                    if s.endswith(', '):
                        txt_new += s[:-2].ljust(len_port) + ','
                    else:
                        txt_new += s.ljust(len_port) + ' '

                    # Add colon or space

                    # If declaration finish with ); insert an eol
                    if m.groups()[6] :
                        txt_new += '\n' + self.char_space*nb_indent + ');'
                    # Add comment
                    if m.groups()[7] :
                        txt_new += ' ' + m.groups()[7]
                else : # No port declaration ? recopy line with just the basic indentation level
                    txt_new += l
                # Remove trailing spaces/tabs and add the end of line
                txt_new = txt_new.rstrip(' \t') + '\n'

        return (txt_new,r)


    # Alignement for signal declaration : [scope::]type [signed|unsigned] [bitwidth] signal list
    def decl_align(self,txt, region):
        lines = txt.splitlines()
        #TODO handle array
        re_str = r'^[ \t]*(\w+\:\:)?(\w+)[ \t]+(signed|unsigned\b)?[ \t]*(\[([\w\:\-` \t]+)\])?[ \t]*(\w+)\b[ \t]*(,[\w, \t]*)?;[ \t]*(.*)'
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
                l += m.groups()[5].ljust(len_max[5])
                # list of signals ? align with other list only
                if m.groups()[6]:
                    if one_decl_per_line:
                        for s in m.groups()[6].split(','):
                            if s != '':
                                l += ';\n' + d + s.strip().ljust(len_max[5])
                    else :
                        l += m.groups()[6].strip().ljust(len_max[6])
                l += ';'
                if m.groups()[7]:
                    l += ' ' + m.groups()[7].strip()
            else : # Not a declaration ? don't touch
                l = line
            txt_new += l + '\n'
        return (txt_new[:-1],region)
