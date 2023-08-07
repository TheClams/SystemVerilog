import sublime_plugin
import re

from .verilogutil import sublimeutil

SCOPES = [
    ('Function' , 'meta.function.body'  , r'^(?s)^\s*.*?\b(\w+)\s*(\(|;)'),
    ('Task'     , 'meta.task.body'      , r'^(?s)^\s*(\w+)'),
    ('Instance' , 'meta.module.inst'    , r'^(?s)^\s*(\w+)\s+(?:#\(:?.*?\)\s*)?(\w+)\s*\('),
    ('Package'  , 'meta.package.body'   , r'^(?s)^\s*package\s+(\w+)'),
    ('Module'   , 'meta.module.body'    , r'^(?s)^\s*module\s+(\w+)'),
    ('Interface', 'meta.interface.body' , r'^(?s)^\s*interface\s+(\w+)'),
    ('Class'    , 'meta.class.body'     , r'^(?s)^\s*class\s+(\w+)'),
]

class VerilogStatus(sublime_plugin.ViewEventListener):

    @classmethod
    def is_applicable(cls,settings):
        return settings.get('sv.status', False) and settings.get('syntax') == 'Packages/SystemVerilog/SystemVerilog.sublime-syntax'

    def on_selection_modified(self):
        self.show_context()

    def on_activated(self):
        self.show_context()

    def show_context(self):
        sel = selection = self.view.sel()
        if len(sel) == 0:
            self.view.erase_status('sv')
            return
        scope = self.view.scope_name(sel[0].a)
        for (n,s,r) in SCOPES:
            if s in scope:
                region = sublimeutil.expand_to_scope(self.view,s,sel[0])
                txt = self.view.substr(region)
                m = re.match(r, txt, re.MULTILINE)
                # if not m:
                #     print('Txt = \n{}'.format(txt))
                #     print('regexp = {}'.format(r))
                if not m:
                    v = n
                elif len(m.groups())==2:
                    v = '{}: {} {}'.format(n,m.group(1),m.group(2))
                else :
                    v = '{}: {}'.format(n,m.group(1))

                self.view.set_status('sv', v)
                return
        self.view.erase_status('sv')