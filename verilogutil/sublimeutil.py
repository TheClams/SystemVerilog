# Some util function linked directly to sublime

import sublime, sublime_plugin
import re, string, os

#filename can be in a unix specific format => convert to windows if needed
def normalize_fname(fname):
    if sublime.platform() == 'windows':
        fname= re.sub(r'/([A-Za-z])/(.+)', r'\1:/\2', fname)
        fname= re.sub(r'/', r'\\', fname)
    return fname

def line_indent(view,point):
    l = view.substr(view.line(point))
    if view.settings().get('translate_tabs_to_spaces'):
        l.replace('\t',' ' * view.settings().get('tab_size',4))
    return len(l) - len(l.lstrip())

#Expand a region to a given scope
def expand_to_scope(view, scope_name, region):

    r_tmp = region
    # print('Init region = ' + str(r_tmp) + ' => text = ' + view.substr(region))
    #Expand forward line by line until scope does not match or end of file is reached
    p = region.b
    scope = view.scope_name(p)
    while scope_name in scope:
        region.b = p
        p = view.find_by_class(p,True,sublime.CLASS_LINE_END)
        scope = view.scope_name(p)
        if p <= region.b:
            # print('End reached')
            break
    # print('Forward line done:' + str(p))
    # Retract backward until we find the scope back
    while scope_name not in scope and p>region.b:
        p=p-1
        scope = view.scope_name(p)
    region.b = p+1
    # print('Retract done:' + str(p) + ' => text = ' + view.substr(region))
    #Expand backward word by word until scope does not match or end of file is reached
    p = region.a
    scope = view.scope_name(p)
    while scope_name in scope:
        region.a = p
        p = view.find_by_class(p,False,sublime.CLASS_LINE_START)
        scope = view.scope_name(p-1)
        if p >= region.a:
            # print('Start reached')
            break
    # print('Backward line done:' + str(p))
    # Retract forward until we find the scope back
    while scope_name not in scope and p<region.a:
        p=p+1
        scope = view.scope_name(p)
    if view.classify(p) & sublime.CLASS_LINE_START == 0:
        region.a = p-1
    # print('Retract done:' + str(p) + ' => text = ' + view.substr(region))
    # print(' Selected region = ' + str(region) + ' => text = ' + view.substr(region))
    return region

#Expand a region to contain a block of text: enclosed by first empty line or comment line
def expand_to_block(view, region):
    r_tmp = region
    # print('Init region = ' + str(r_tmp) + ' => text = ' + view.substr(region))
    #Expand backward word by word until scope does not match or end of file is reached
    p = view.find_by_class(region.a,False,sublime.CLASS_LINE_START)
    scope = view.scope_name(p)
    ilvl = line_indent(view,region.a)
    ilvl_tmp = ilvl
    while ('comment' not in scope or ilvl_tmp>ilvl) and (view.classify(p) & sublime.CLASS_EMPTY_LINE) == 0:
        region.a = p
        if ilvl_tmp < ilvl:
            ilvl = ilvl_tmp
        p = view.find_by_class(p,False,sublime.CLASS_LINE_START)
        if view.substr(p) in [' ', '\t'] and ((view.classify(p) & sublime.CLASS_EMPTY_LINE) == 0) :
            pp = view.find_by_class(p,True,sublime.CLASS_WORD_START|sublime.CLASS_SUB_WORD_START|sublime.CLASS_PUNCTUATION_START)
            scope = view.scope_name(pp)
        else:
            scope = view.scope_name(p)
        ilvl_tmp = line_indent(view,p)
        if p >= region.a:
            break
    region.a = view.find_by_class(p,True,sublime.CLASS_LINE_START)
    # print('Backward done:' + str(region.a) + ' => text = ' + view.substr(region))
    #Expand forward line by line until we reach a comment or an empty line
    p = view.find_by_class(region.b,True,sublime.CLASS_LINE_START)
    scope = view.scope_name(p)
    ilvl_tmp = line_indent(view,region.b)
    while ('comment' not in scope or ilvl_tmp>ilvl) and (view.classify(p) & sublime.CLASS_EMPTY_LINE) == 0:
        region.b = p
        if ilvl_tmp < ilvl:
            ilvl = ilvl_tmp
        p = view.find_by_class(p,True,sublime.CLASS_LINE_START)
        if view.substr(p) in [' ', '\t'] and ((view.classify(p) & sublime.CLASS_EMPTY_LINE) == 0) :
            pp = view.find_by_class(p,True,sublime.CLASS_WORD_START|sublime.CLASS_SUB_WORD_START|sublime.CLASS_PUNCTUATION_START)
            scope = view.scope_name(pp)
        else:
            scope = view.scope_name(p)
        ilvl_tmp = line_indent(view,p)
        if p <= region.b:
            break
    region.b = p - 1
    # print('Forward done:' + str(region.b) + ' => text = ' + view.substr(region))
    print(' Selected region = ' + str(region) + ' => text = ' + view.substr(region))
    return region


# Create a panel and display a text
def print_to_panel(txt,name):
    window = sublime.active_window()
    v = window.create_output_panel(name)
    v.run_command('append', {'characters': txt})
    window.run_command("show_panel", {"panel": "output."+name})

# Move cursor to the beginning of a region
def move_cursor(view,pos):
    view.sel().clear()
    view.sel().add(sublime.Region(pos,pos))
    view.show(pos)
