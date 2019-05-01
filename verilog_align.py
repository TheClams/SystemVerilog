import sublime, sublime_plugin
import re, string, os, sys, imp

try:
    from .verilogutil import verilogutil
    from .verilogutil import verilog_beautifier
    from .verilogutil import sublimeutil
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'verilogutil'))
    import verilogutil
    import sublimeutil
    import verilog_beautifier

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(verilog_beautifier)
    imp.reload(sublimeutil)

class VerilogAlign(sublime_plugin.TextCommand):

    def run(self,edit, cmd=""):
        if len(self.view.sel())==0 : return
        # TODO: handle multi cursor. Currently only first one ise used
        # Expand the selection to a complete scope supported by the one of the align function
        # Get sublime setting
        self.settings = self.view.settings()
        tab_size = int(self.settings.get('tab_size', 4))
        char_space = ' ' * tab_size
        use_space = self.settings.get('translate_tabs_to_spaces')
        oneBindPerLine = self.settings.get('sv.one_bind_per_line',True)
        oneDeclPerLine = self.settings.get('sv.one_decl_per_line',True)
        paramOneLine = self.settings.get('sv.param_oneline',True)
        instAlign = self.settings.get('sv.param_port_alignment',True)
        indentStyle = self.settings.get('sv.indent_style',True)
        stripEmptyLine = self.settings.get('sv.strip_empty_line',True)
        ignoreTick = self.settings.get('sv.alignment_ignore_tick',False)
        importSameLine = self.settings.get('sv.mod_import_same_line',False)
        align_comma = self.settings.get('sv.align_comma_semicolon',False)
        beautifier = verilog_beautifier.VerilogBeautifier(tab_size, not use_space, oneBindPerLine, oneDeclPerLine, paramOneLine, indentStyle, False, stripEmptyLine,instAlign,ignoreTick,importSameLine,align_comma)
        if not use_space:
            char_space = '\t'
        region = self.view.sel()[0]
        row,col = self.view.rowcol(region.a)
        scope = self.view.scope_name(region.a)
        if region.b != region.a :
            if self.view.scope_name(region.b) != scope :
                scope = ''
        txt = ''
        # print('[VerilogAlign] Region= {}, Scope = {} -- {})'.format(region,scope,self.view.scope_name(region.b)))
        if cmd == 'reindent':
            # Select whole text if nothing is selected
            # Otherwise expand to the line
            if region.empty():
                region = sublime.Region(0,self.view.size())
            else :
                region = self.view.line(self.view.sel()[0])
            beautifier.settings['reindentOnly'] = True
            txt = beautifier.beautifyText(self.view.substr(region))
        elif 'meta.module.inst' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.inst',region)
            # Make sure to get complete line to be able to get initial indentation
            region = self.view.line(region)
            txt = self.view.substr(region)
            # print('[VerilogAlign] Scope inst : expanding to {}'.format(region))
            ilvl = beautifier.getIndentLevel(txt)
            txt = beautifier.alignInstance(txt,ilvl)
        elif 'meta.module.systemverilog' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.systemverilog',region)
            # print('[VerilogAlign] Scope Module: expanding to {}'.format(region))
            txt = beautifier.alignModulePort(self.view.substr(region),0)
        else :
            # empty region ? select all lines before and after until an empty line is found
            if region.empty():
                region = sublimeutil.expand_to_block(self.view,region)
                # try to find begin/end block
                kw_l = ['begin','end','case','endcase','module','endmodule','function','endfunction','task','endtask','class','endclass']
                txt = verilogutil.clean_comment(self.view.substr(region))
                # print('Initial region = {}\n{}\n-------------'.format(region,txt))
                cnt = {}
                for kw in kw_l:
                    f = re.findall(r'\b{}\b'.format(kw),txt)
                    cnt[kw] = len(f)
                # print(cnt)
                if(cnt['module']!=cnt['endmodule']):
                    if cnt['module']>0:
                        r_stop = self.view.find(r'\bendmodule\b',region.a)
                        if r_stop.b!=-1:
                            region.b = r_stop.b
                    else:
                        _,_,rl  = sublimeutil.find_closest(self.view,region,r'\bmodule\b')
                        if len(rl)>0 and rl[-1].b!=-1:
                            region.a = rl[-1].a
                elif(cnt['class']!=cnt['endclass']):
                    if cnt['class']>0:
                        r_stop = self.view.find(r'\bendclass\b',region.a)
                        if r_stop.b!=-1:
                            region.b = r_stop.b
                    else:
                        _,_,rl  = sublimeutil.find_closest(self.view,region,r'\bclass\b')
                        if len(rl)>0 and rl[-1].b!=-1:
                            region.a = rl[-1].a
                elif(cnt['function']!=cnt['endfunction']):
                    if cnt['function']>0:
                        r_stop = self.view.find(r'\bendfunction\b',region.a)
                        if r_stop.b!=-1:
                            region.b = r_stop.b
                    else:
                        _,_,rl  = sublimeutil.find_closest(self.view,region,r'\bfunction\b')
                        if len(rl)>0 and rl[-1].b!=-1:
                            region.a = rl[-1].a
                elif(cnt['task']!=cnt['endtask']):
                    if cnt['task']>0:
                        r_stop = self.view.find(r'\bendtask\b',region.a)
                        if r_stop.b!=-1:
                            region.b = r_stop.b
                    else:
                        _,_,rl  = sublimeutil.find_closest(self.view,region,r'\btask\b')
                        if len(rl)>0 and rl[-1].b!=-1:
                            region.a = rl[-1].a
                elif(cnt['begin']!=cnt['end']):
                    wl = []
                    rl = self.view.find_all(r'\b(begin|end)\b',0,'$1',wl)
                    cnt_diff = cnt['begin'] - cnt['end']
                    if rl :
                        idx = 0
                        # More begin than end ? Expand forward for the missing end
                        if cnt_diff > 0:
                            # Find first region following initial block
                            while idx<len(rl) and rl[idx].b < region.b :
                                idx += 1
                            # Iterate over following begin/end until the difference of begin end is 0
                            while idx<len(rl) and cnt_diff>0 :
                                if wl[idx] == 'begin':
                                    cnt_diff += 1
                                else :
                                    cnt_diff -= 1
                                if cnt_diff > 0:
                                    idx += 1
                            region.b = rl[idx].b
                        # More end than begin ? Expand backward for the missing begin
                        else:
                            # Find first region preceding initial block
                            while idx<len(rl) and rl[idx].a < region.a :
                                idx += 1
                            if idx>0:
                                idx -= 1
                            # Iterate over following begin/end until the difference of begin end is 0
                            while idx<len(rl) and cnt_diff<0 :
                                if wl[idx] == 'begin':
                                    cnt_diff += 1
                                else :
                                    cnt_diff -= 1
                                if cnt_diff < 0:
                                    idx -= 1
                            region.a = rl[idx].a
                if self.view.classify(region.a) & sublime.CLASS_LINE_START == 0:
                    p = self.view.find_by_class(region.a,False,sublime.CLASS_LINE_START)
                    if p>=0 and p<region.a:
                        region.a = p
                if self.view.classify(region.b) & sublime.CLASS_LINE_END == 0:
                    p = self.view.find_by_class(region.b,True,sublime.CLASS_LINE_END)
                    if p>-1 and self.view.classify(p) & sublime.CLASS_LINE_END == 0:
                        region.b = p-1
                    elif p>region.b:
                        region.b = p
            else:
                region = self.view.line(self.view.sel()[0])
            if self.view.classify(region.b) & sublime.CLASS_EMPTY_LINE :
                region.b -= 1
            if self.view.classify(region.a) & sublime.CLASS_EMPTY_LINE :
                region.a += 1
            txt = self.view.substr(region)
            # print('Final region = {}\n{}\n-------------'.format(region,txt))
            # print(txt)
            txt = beautifier.beautifyText(txt)
        if txt:
            self.view.replace(edit,region,txt)
            sublimeutil.move_cursor(self.view,self.view.text_point(row,col))
        else :
            sublime.status_message('No alignement support for this block of code.')
