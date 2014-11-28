# Some util function linked directly to sublime

import sublime, sublime_plugin
import re, string, os

#filename can be in a unix specific format => convert to windows if needed
def normalize_fname(fname):
    if sublime.platform() == 'windows':
        fname= re.sub(r'/([A-Za-z])/(.+)', r'\1:/\2', fname)
        fname= re.sub(r'/', r'\\', fname)
    return fname

#Expand a selection to a given scope
def expand_to_scope(view, scope_name, region):
    r = region
    scope = view.scope_name(region.a)
    cnt = 0 # keep timeout in case the test on region not growing is not enough (should be removed once tested enough)
    while scope_name in scope and cnt <8:
        r = region
        region=view.extract_scope(r.b)
        scope = view.scope_name(region.a)
        # Failed to expand from b? try from a
        if scope_name not in scope:
            region=view.extract_scope(r.a)
            scope = view.scope_name(region.a)
        cnt=cnt+1
        # if selection did not grow on the expand, just get out of the loop
        if (region.b-region.a)<=(r.b-r.a):
            break
    if cnt == 8:
        print("[expand_to_scope] Unexpected TIMEOUT !!!")
    return r

def print_to_panel(txt,name):
    window = sublime.active_window()
    v = window.create_output_panel(name)
    v.run_command('append', {'characters': txt})
    window.run_command("show_panel", {"panel": "output."+name})


def move_cursor(view,r):
    r.a = r.a + 1
    r.b = r.a
    view.sel().clear()
    view.sel().add(r)
    view.show(r.a)
