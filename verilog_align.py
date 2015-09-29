import sublime, sublime_plugin
import re, string, os, sys, imp

try:
    from SystemVerilog.verilogutil import verilogutil
    from SystemVerilog.verilogutil import verilog_beautifier
    from SystemVerilog.verilogutil import sublimeutil
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
        if len(self.view.sel())==0 : return;
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
        beautifier = verilog_beautifier.VerilogBeautifier(tab_size, not use_space, oneBindPerLine, oneDeclPerLine, paramOneLine, indentStyle, False, stripEmptyLine,instAlign)
        current_pos = self.view.viewport_position( )
        if not use_space:
            char_space = '\t'
        region = self.view.sel()[0]
        region_start = region
        scope = self.view.scope_name(region.a)
        if region.b > region.a :
            if self.view.scope_name(region.b) != scope :
                scope = ''
        txt = ''
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
            ilvl = beautifier.getIndentLevel(txt)
            txt = beautifier.alignInstance(txt,ilvl)
        elif 'meta.module.systemverilog' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.systemverilog',region)
            txt = beautifier.alignModulePort(self.view.substr(region),0)
        else :
            # empty region ? select all lines before and after until an empty line is found
            if region.empty():
                region = sublimeutil.expand_to_block(self.view,region)
            else:
                region = self.view.line(self.view.sel()[0])
            if self.view.classify(region.b) & sublime.CLASS_EMPTY_LINE :
                region.b -= 1;
            if self.view.classify(region.a) & sublime.CLASS_EMPTY_LINE :
                region.a += 1;
            txt = self.view.substr(region)
            txt = beautifier.beautifyText(txt)
        if txt:
            self.view.replace(edit,region,txt)
            sublimeutil.move_cursor(self.view,region_start.a)
        else :
            sublime.status_message('No alignement support for this block of code.')
