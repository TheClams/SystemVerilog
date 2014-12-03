# Some util function linked directly to sublime

import sublime, sublime_plugin
import re, string, os

#filename can be in a unix specific format => convert to windows if needed
def normalize_fname(fname):
    if sublime.platform() == 'windows':
        fname= re.sub(r'/([A-Za-z])/(.+)', r'\1:/\2', fname)
        fname= re.sub(r'/', r'\\', fname)
    return fname

#Expand a region to a given scope
def expand_to_scope(view, scope_name, region):
    scope = view.scope_name(region.a)
    r_tmp = region
    #Expand forward word by word until scope does not match or end of file is reached
    while scope in scope_name:
        region.b = r_tmp.b
        r_tmp = self.view.find_by_class(region.b,True,sublime.CLASS_WORD_END)
        if r_tmp.b <= region.b:
            break
    #Expand backward word by word until scope does not match or end of file is reached
    while scope in scope_name:
        region.a = r_tmp.a
        r_tmp = self.view.find_by_class(region.a,False,sublime.CLASS_WORD_START)
        if r_tmp.a >= region.a:
            break
    return region


# Create a panel and display a text
def print_to_panel(txt,name):
    window = sublime.active_window()
    v = window.create_output_panel(name)
    v.run_command('append', {'characters': txt})
    window.run_command("show_panel", {"panel": "output."+name})

# Move cursor to the beginning of a region
def move_cursor(view,r):
    r.a = r.a + 1
    r.b = r.a
    view.sel().clear()
    view.sel().add(r)
    view.show(r.a)
