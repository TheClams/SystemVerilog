import sublime, sublime_plugin
import re, string, os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
import verilogutil

class VerilogAlign(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())!=1 : return; # No multi-selection allowed (yet?)
        # Expand the selection to a complete scope supported by the one of the align function
        # Get sublime setting
        settings = self.view.settings()
        self.tab_size = int(settings.get('tab_size', 4))
        self.char_space = ' ' * self.tab_size
        self.use_space = settings.get('translate_tabs_to_spaces')
        if not self.use_space:
            self.char_space = '\t'
        region = self.view.extract_scope(self.view.sel()[0].a)
        scope = self.view.scope_name(region.a)
        txt = ''
        if 'meta.module.inst' in scope:
            (txt,region) = self.inst_align(region)
        elif 'meta.module.systemverilog' in scope:
            (txt,region) = self.port_align(region)
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
        cnt = 0 # counter for timeout of expand selection (to avoid infinite loop, was needed in debug at least)
        scope = 'meta.module.inst'
        # Expand selection until we get the whole module instantiation
        while 'meta.module.inst' in scope and cnt<8:
            r = region
            # print(self.view.substr(r))
            region=self.view.extract_scope(r.b)
            cnt=cnt+1
            scope = self.view.scope_name(region.a)
            # print('ITERATION ' + str(cnt) + ': next scope = ' + scope)
        # Make sure to get complete line to be able to get initial indentation
        r = self.view.expand_by_class(r,sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
        txt = self.view.substr(r).rstrip()
        # print (txt)
        # Realign text
        # bind = re.findall(r'\.\s*(?P<port>\w+)\s*\(\s*(?P<signal>[\w\[\]\:~\{\}\s]+)\s*\)[\s]*(?P<sep>,|\))?\s*?(?P<comment>/.*?)?$',txt,re.MULTILINE)
        re_str = r'\.\s*(\w+)\s*\(\s*([\w\[\]\:~`\+-\{\}\s\'&|]*)\s*\)[\s]*'
        bind = re.findall(re_str,txt,re.MULTILINE)
        len_port    = max([len(x[0]) for x in bind])
        len_signals = max([len(x[1].rstrip()) for x in bind])
        txt_new = ''
        lines = txt.splitlines()
        nb_indent = self.get_indent_level(lines[0])
        for i,line in enumerate(lines):
            # Remove leading and trailing space. add end of line
            l = line.lstrip().rstrip() + '\n'
            #Special case of first line: potentially insert an end of line between instance name and port name
            if i==0:
                txt_new += self.char_space*nb_indent+l
            else :
                if i == len(lines)-1:
                    txt_new += self.char_space*(nb_indent)
                else:
                    txt_new += self.char_space*(nb_indent+1)
                m = re.search(r'^'+re_str+r'(,|\))?\s*(.*)',l)
                if m:
                    # print('Line ' + str(i) + ' : ' + str(m.groups()))
                    txt_new += '.' + m.groups()[0].ljust(len_port)
                    txt_new += '(' + m.groups()[1].rstrip().ljust(len_signals) + ')'
                    if m.groups()[2]:
                        if m.groups()[2]==')' :
                            txt_new += l[-1] + self.char_space*nb_indent + ')'
                        else:
                            txt_new += m.groups()[2] + ' '
                    else:
                        txt_new += '  '
                    if m.groups()[3]:
                        txt_new += m.groups()[3]
                    txt_new += l[-1]
                else : # No port binding ? recopy line with just the basic indentation level
                    txt_new += l
        return (txt_new,r)

    # Alignement for port declaration (for ansi-style)
    def port_align(self,region):
        cnt = 0 # counter for timeout of expand selection (to avoid infinite loop, was needed in debug at least)
        scope = 'meta.module.systemverilog'
        # Expand selection until we get the whole module instantiation
        while 'meta.module.systemverilog' in scope and cnt<8:
            r = region
            region=self.view.extract_scope(r.b)
            cnt=cnt+1
            scope = self.view.scope_name(region.a)
        r = self.view.expand_by_class(r,sublime.CLASS_LINE_START | sublime.CLASS_LINE_END)
        txt = self.view.substr(r)
        #TODO: handle interface
        # Port declaration: direction type? signess? buswidth? portlist ,? comment?
        re_str = r'^[ \t]*(\w+)[ \t]+(\w+\b)?[ \t]*(\w+\b)?[ \t]*(\[([\w\:\-` \t]+)\])?[ \t]*(\w+[\w, \t]*)'
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
            l = line.lstrip().rstrip()
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
                            txt_new += ' [' + m.groups()[4].strip().rjust(len_bw) + '] '
                        else:
                            txt_new += ''.rjust(len_bw+4)
                    # Add port list: space every port in the list by just on space
                    s = re.sub(r',',', ',re.sub(r'\s*','',m.groups()[5]))
                    if s.endswith(', '):
                        txt_new += s[:-2].ljust(len_port) + ','
                    else:
                        txt_new += s.ljust(len_port)

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

