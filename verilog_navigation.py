from __future__ import absolute_import

import sublime, sublime_plugin
import re, string, os, sys, functools, mmap, pprint, imp, threading
from collections import Counter
from plistlib import readPlistFromBytes

from . import verilog_module
from .verilogutil import verilogutil
from .verilogutil import sublimeutil
from .color_scheme_util import st_color_scheme_matcher
from .color_scheme_util import rgba

############################################################################
# Init
TOOLTIP_SUPPORT = int(sublime.version()) >= 3072

use_tooltip = False
show_ref = False
show_signal_links = False
debug = False
sv_settings = None
tooltip_css = ''
tooltip_flag = 0
navBar = {}
colors = {}

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(sublimeutil)
    imp.reload(verilog_module)
    imp.reload(st_color_scheme_matcher)
    global sv_settings
    global pref_settings
    global debug
    pref_settings = sublime.load_settings('Preferences.sublime-settings')
    pref_settings.clear_on_change('reload')
    pref_settings.add_on_change('reload',plugin_loaded)
    sv_settings = sublime.load_settings('SystemVerilog.sublime-settings')
    sv_settings.clear_on_change('reload')
    sv_settings.add_on_change('reload',plugin_loaded)
    debug =  sv_settings.get("sv.debug")
    if debug:
        print('[SV:Popup] Plugin Loaded')
    init_css()

def init_css():
    global use_tooltip
    global tooltip_css
    global tooltip_flag
    global show_ref
    global show_signal_links
    global colors
    if int(sublime.version()) >= 3072 :
        use_tooltip = sv_settings.get('sv.tooltip',True)
        show_signal_links = sv_settings.get('sv.tooltip_show_signal_links',False)
        if sv_settings.get('sv.tooltip_hide_on_move',True):
            tooltip_flag = sublime.HIDE_ON_MOUSE_MOVE_AWAY
        else:
            tooltip_flag = 0
        show_ref = int(sublime.version()) >= 3145 and sv_settings.get('sv.tooltip_show_refs',True)
        #
        scheme = st_color_scheme_matcher.ColorSchemeMatcher(pref_settings.get('color_scheme'))
        bg = scheme.get_special_color('background')
        fg = scheme.get_special_color('foreground')
        # Create background and border color based on the background color
        bg_rgb = rgba.RGBA(bg)
        if bg_rgb.b > 128:
            bgHtml = bg_rgb.b - 0x33
            bgBody = bg_rgb.b - 0x20
        else:
            bgHtml = bg_rgb.b + 0x33
            bgBody = bg_rgb.b + 0x20
        if bg_rgb.g > 128:
            bgHtml += (bg_rgb.g - 0x33)<<8
            bgBody += (bg_rgb.g - 0x20)<<8
        else:
            bgHtml += (bg_rgb.g + 0x33)<<8
            bgBody += (bg_rgb.g + 0x20)<<8
        if bg_rgb.r > 128:
            bgHtml += (bg_rgb.r - 0x33)<<16
            bgBody += (bg_rgb.r - 0x20)<<16
        else:
            bgHtml += (bg_rgb.r + 0x33)<<16
            bgBody += (bg_rgb.r + 0x20)<<16
        tooltip_css = 'html {{ background-color: #{bg:06x}; color: {fg}; }}\n'.format(bg=bgHtml, fg=fg)
        tooltip_css+= 'body {{ background-color: #{bg:06x}; margin: 1px; font-size: 1em; }}\n'.format(bg=bgBody)
        tooltip_css+= 'p {padding-left: 0.6em;}\n'
        tooltip_css+= '.content {margin: 0.8em;}\n'
        tooltip_css+= 'h1 {font-size: 1.0rem;font-weight: bold; margin: 0 0 0.25em 0;}\n'
        tooltip_css+= 'a {{color: {c};}}\n'.format(c=fg)
        tooltip_css+= '.keyword {{color: {c};}}\n'.format(c=scheme.get_color('keyword'))
        tooltip_css+= '.support {{color: {c};}}\n'.format(c=scheme.get_color('support'))
        tooltip_css+= '.storage {{color: {c};}}\n'.format(c=scheme.get_color('storage'))
        tooltip_css+= '.function {{color: {c};}}\n'.format(c=scheme.get_color('support.function'))
        tooltip_css+= '.entity {{color: {c};}}\n'.format(c=scheme.get_color('entity'))
        tooltip_css+= '.operator {{color: {c};}}\n'.format(c=scheme.get_color('keyword.operator'))
        tooltip_css+= '.numeric {{color: {c};}}\n'.format(c=scheme.get_color('constant.numeric'))
        tooltip_css+= '.string {{color: {c};}}\n'.format(c=scheme.get_color('string'))
        tooltip_css+= '.extra-info {font-size: 0.9em; }\n'
        tooltip_css+= '.ref_links {font-size: 0.9em; color: #0080D0; padding-left: 0.6em}\n'
        colors['operator'] = scheme.get_color('keyword.operator')
    else :
       use_tooltip  = False
       tooltip_css = ''

############################################################################
callbacks_on_load = {}

class VerilogOnLoadEventListener(sublime_plugin.EventListener):
    # Called when a file is finished loading.
    def on_load_async(self, view):
        global callbacks_on_load
        if view.file_name() in callbacks_on_load:
            callbacks_on_load[view.file_name()]()
            del callbacks_on_load[view.file_name()]


############################################################################
# Display type of the signal/variable under the cursor into the status bar #
class VerilogTypePopup :
    def __init__(self,view):
        self.view = view

    def show(self,region,location):
        # If nothing is selected expand selection to word
        if region.empty() :
            region = self.view.word(region)
        # Make sure a whole word is selected
        elif (self.view.classify(region.a) & sublime.CLASS_WORD_START)==0 or (self.view.classify(region.b) & sublime.CLASS_WORD_END)==0:
            if (self.view.classify(region.a) & sublime.CLASS_WORD_START)==0:
                region.a = self.view.find_by_class(region.a,False,sublime.CLASS_WORD_START)
            if (self.view.classify(region.b) & sublime.CLASS_WORD_END)==0:
                region.b = self.view.find_by_class(region.b,True,sublime.CLASS_WORD_END)
        # Optionnaly extend selection to parent object (parent.var)
        if 'support.function.port' not in self.view.scope_name(region.a):
            while region.a>1 and self.view.substr(sublime.Region(region.a-1,region.a))=='.' :
                c = self.view.substr(sublime.Region(region.a-2,region.a-1))
                # Array selection -> extend to start of array
                if c == ']':
                    region.a = self.view.find_by_class(region.a-3,False,sublime.CLASS_WORD_START)
                if self.view.classify(region.a-2) & sublime.CLASS_WORD_START:
                    region.a = region.a-2
                else :
                    region.a = self.view.find_by_class(region.a-2,False,sublime.CLASS_WORD_START)
        # Optionnaly extend selection to scope specifier
        if region.a>2 and self.view.substr(sublime.Region(region.a-2,region.a))=='::' :
            region.a = self.view.find_by_class(region.a-3,False,sublime.CLASS_WORD_START)
        v = self.view.substr(region)
        if debug:  print('[SV:Popup.show] Word to show = {0}'.format(v));
        if re.match(r'^([A-Za-z_]\w*::|(([A-Za-z_]\w*(\[.+\])?)\.)+)?[A-Za-z_]\w*$',v): # Check this is a valid word
            s,ti,colored,is_local = self.get_type(v,region)
            # print('s={},is_local={}, ti={},colored={}'.format(s,is_local,ti,colored))
            ref_name = ''
            if not s:
                sublime.status_message('No definition found for ' + v)
            # Check if we use tooltip or statusbar to display information
            elif use_tooltip :
                if debug:  print('[SV:Popup.show] {} (colored={})'.format(ti,colored));
                s_func = '<br><span class="extra-info">{0}<span class="keyword">function </span><span class="function">{1}</span>()</span>' # tempalte for printing function info
                if ti and (ti['type'] in ['module','interface','function','task']):
                    ref_name = ti['name']
                    s,_ = self.color_str(s=s, addLink=True,ti_var=ti)
                    if 'param' in ti:
                        s += self.add_info(ti['param'],fieldTemplate='DNV-parameter')
                    if 'port' in ti:
                        s += self.add_info(ti['port'])
                    if ti['type']=='interface':
                        if 'signal' not in ti and 'fname' in ti:
                            ti = verilogutil.parse_module_file(ti['fname'][0],ti['name'])
                        if ti:
                            if 'signal' in ti:
                                s += self.add_info([x for x in ti['signal'] if x['tag']=='decl'])
                            if 'modport' in ti:
                                s += self.add_info(ti['modport'],fieldTemplate='modport {0}', field='name')
                elif ti and ti['type'] == 'clocking':
                    s,_ = self.color_str(s=s, addLink=True,ti_var=ti)
                    for p in ti['port']:
                        x = '{} {}'.format(p['type'],p['name'])
                        s += '<br><span class="extra-info">{}{}</span>'.format('&nbsp;'*4,self.color_str(x)[0])
                elif ti and 'tag' in ti and (ti['tag'] == 'enum' or ti['tag']=='struct'):
                    m = re.search(r'(?s)^(.*)\{(.*)\}', ti['decl'])
                    s,tti = self.color_str(s=m.groups()[0] + ' ' + v, addLink=True)
                    if ti['tag'] == 'enum':
                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[1])
                    else :
                        fti = verilogutil.get_all_type_info(m.groups()[1])
                        if fti:
                            s += self.add_info(fti)
                elif ti and ti['type']=='class':
                    ref_name = ti['name']
                    if 'fname' in ti:
                        ci = verilogutil.parse_class_file(ti['fname'][0],ti['name'])
                    else :
                        txt = self.view.substr(sublime.Region(0, self.view.size()))
                        ci = verilogutil.parse_class(txt,ti['name'])
                    s,_ = self.color_str(s='class {0}'.format(ti['name']), addLink=True,ti_var=ti)
                    if ci:
                        if ci['extend']:
                            s+=' <span class="keyword">extends</span> '
                            s+='<span class="storage">{0}</span>'.format(ci['extend'])
                        s += self.add_info([x for x in ci['member'] if 'access' not in x])
                        s += self.add_info([x for x in ci['function'] if 'access' not in x and x['name']!='new'],field='name',template=s_func, useColor=False)
                    #if debug: print(ci);
                elif ti and ti['type']=='package':
                    s,_ = self.color_str(s=s, addLink=True,ti_var=ti)
                    if 'member' in ti:
                        members = []
                        for x in ti['member']:
                            m = re.match(r'(?P<decl>(typedef\s+)?enum\s+([^\{]*))\{(?P<val>.*)\}\s*(?P<name>[^;]*)',x['decl'])
                            if m :
                                d = '{} {}'.format(m.group('decl'),m.group('name'))
                                for v in m.group('val').split(','):
                                    d+=' <br>{}{}'.format('&nbsp;'*8,v.strip())
                            else :
                                d = re.sub(r'struct\s+(packed\s*)(\{.*\})',r'struct \1',x['decl'])
                            members.append({'decl' : d})
                        s += self.add_info(members)
                        # s += self.add_info([x for x in ti['member']])
                elif not colored :
                    s,ti = self.color_str(s=s, addLink=True)
                    if ti:
                        if debug: print('Default : {}'.format(ti))
                        if 'tag' in ti and ti['tag'] == 'enum':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[0])
                        elif 'tag' in ti and ti['tag'] == 'struct':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                fti = verilogutil.get_all_type_info(m.groups()[0])
                                if fti:
                                    s += self.add_info(fti)
                        elif ti['decl'] and 'interface' in ti['decl']:
                            mi = verilog_module.lookup_module(self.view,ti['name'])
                            if mi :
                                # pprint.pprint(mi)
                                if 'param' in mi:
                                    s += self.add_info(mi['param'],fieldTemplate='DNV-parameter')
                                if 'signal' in mi:
                                    s += self.add_info([x for x in mi['signal'] if x['tag']=='decl'])
                                if 'modport' in mi:
                                    s += self.add_info(mi['modport'],fieldTemplate='modport {0}', field='name')
                        elif ti['type']=='class':
                            ci = verilogutil.parse_class_file(ti['fname'][0],ti['name'])
                            if ci:
                                s += self.add_info([x for x in ci['member'] if 'access' not in x])
                                s += self.add_info([x for x in ci['function'] if 'access' not in x and x['name']!='new'],field='name',template=s_func, useColor=False)
                # Add reference list
                if show_ref and ref_name :
                    refs = self.view.window().lookup_references_in_index(ref_name)
                    if refs:
                        ref_links = []
                        for l in refs :
                            l_href = '{}:{}:{}'.format(l[0],l[2][0],l[2][1])
                            l_name = os.path.basename(l[0])
                            ref_links.append('<a href="LINK@{}" class="ref_links">{}</a>'.format(l_href,l_name))
                        s += '<h1><br>Reference:</h1><span>{}</span>'.format('<br>'.join(ref_links))
                elif is_local and show_signal_links:
                    s += '<span><br><a href="DRIVER@__CURRENT__@{}" class="ref_links">Goto Driver</a><br>'.format(v)
                    s += '<a href="REFERENCE@__CURRENT__@{}" class="ref_links">Goto Reference</a></span>'.format(v)
                s = '<style>{css}</style><div class="content">{txt}</div>'.format(css=tooltip_css, txt=s)
                # print(s)
                self.view.show_popup(s,location=location, flags=tooltip_flag, max_width=500, on_navigate=self.on_navigate)
            else :
                # fix hard limit to signal declaration to 128 to ensure it can be displayed
                if s and len(s) > 128:
                    s = re.sub(r'\{.*\}','',s) # A long signal is typical of an enum, struct : remove content to only let the type appear
                    if len(s) > 128:
                        s = s[:127]
                sublime.status_message(s)

    def add_info(self, ilist, field='decl', template='<br><span class="extra-info">{0}{1}</span>', space=4, limit=256, useColor=True, fieldTemplate='{0}'):
        s = ''
        cnt = 0;
        for x in ilist:
            if fieldTemplate.startswith('DNV'):
                f = fieldTemplate[4:]+' {d} {n} = {v}'
                f = f.format(d=x['decl'],n=x['name'],v=x['value'])
            else :
                f = fieldTemplate.format(x[field])
            if useColor:
                f = self.color_str(f)[0]
            s += template.format('&nbsp;'*space,f)
            cnt += 1
            if cnt >= limit:
                s+='<br><span class="extra-info">continuing ...</span>'
                break
        return s

    def get_type(self,var_name,region):
        vs = None
        is_local = False
        if '::' in var_name:
            vs = var_name.split('::')
            var_name = vs[1]
            scope = self.view.scope_name(region.a+len(vs[0])+2)
        else:
            scope = self.view.scope_name(region.a)
        ti = None
        colored = False
        txt = ''
        if debug: print ('[SV:Popup.get_type] var={0} scope="{1}"'.format(var_name,scope));
        # In case of field, retrieve parent type
        if '.' in var_name:
            ti = verilog_module.type_info_on_hier(self.view,var_name,region=region)
            if ti:
                # print('[SV:get_type] Return {0}'.format(ti))
                txt = ti['decl']
        # Extract type info from module if we are on port connection
        elif 'support.function.port' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.inst',region)
            s = self.view.substr(region)
            m = re.match(r'^(?s)\s*(\w+)\s+(\w+)',s,re.MULTILINE)
            if not m:
                m = re.match(r'^(?s)\s*(\w+)\s*#(?:.*?)\)\s*(\w+)',s,re.MULTILINE)
                if not m:
                    m = re.match(r'^(?s)\s*(\w+)()',s,re.MULTILINE)
            if not m:
                print('[SV:Popup.get_type] Unable to extract the module name in {}'.format(s))
                return
            mname = m.group(1)
            iname = m.group(2)
            # print('[get_type] Find module with name {} (instance {})'.format(mname,iname))
            mi = verilog_module.lookup_module(self.view,mname)
            if mi:
                colored = True
                found = False
                fname = '{0}:{1}:{2}'.format(mi['fname'][0],mi['fname'][1],mi['fname'][2])
                for p in mi['port']:
                    if p['name']==var_name:
                        txt,_ = self.color_str(s=p['decl'].rsplit(' ',1)[0],last_word=False)
                        if p['decl'].startswith('in'): # Input or inout
                            txt += ' <a href="REFERENCE@{0}@{1}">{1}</a>'.format(mi['fname'][0],var_name)
                        elif p['decl'].startswith('output'): # output
                            txt += ' <a href="DRIVER@{0}@{1}">{1}</a>'.format(mi['fname'][0],var_name)
                        else:
                            txt += ' {0}'.format(var_name)
                        found = True
                        break
                # Check parameters if this was not found in port name
                if not found:
                    for p in mi['param']:
                        if p['name']==var_name:
                            txt,_ = self.color_str(s='  parameter {0} {1} = {2}'.format(p['decl'],p['name'],p['value']))
                if sv_settings.get('sv.tooltip_show_module_on_port',False):
                    txt = '<a href="LINK@{0}" class="storage">{1}</a><span class="entity"> {2}</span><br>  {3}'.format(fname,mname,iname,txt)
        # Get function I/O
        elif 'support.function.generic' in scope or 'entity.name.function' in scope:
            ti = verilog_module.lookup_function(self.view,var_name)
            if debug: print ('[get_type] Function: {0}'.format(ti))
            if ti:
                txt = ti['decl']
        # Get structure/interface
        elif 'storage.type.userdefined' in scope or 'storage.type.uvm' in scope or 'storage.type.interface' in scope:
            ti = verilog_module.lookup_type(self.view,var_name)
            if ti:
                txt = ti['decl']
        # Get Module I/O
        elif 'storage.type.module' in scope:
            ti = verilog_module.lookup_module(self.view,var_name)
            if ti:
                txt = ti['type'] + ' ' + var_name
        # Get Package info
        elif 'support.type.scope' in scope:
            ti = verilog_module.lookup_package(self.view,var_name)
            if ti:
                txt = 'package {0}'.format(var_name)
        # Get Macro text
        elif 'constant.other.define' in scope:
            txt,_ = verilog_module.lookup_macro(self.view,var_name)
        # Get Base Class
        elif 'entity.other.inherited-class' in scope:
            ti = verilog_module.lookup_type(self.view,var_name)
            if ti:
                txt = ti['decl']
        # Variable inside a scope
        elif vs:
            if len(vs)==2:
                ti = verilog_module.lookup_type(self.view,vs[0])
                if ti and ti['type']=='package':
                    ti = verilog_module.type_info_file(self.view,ti['fname'][0],vs[1])
                    if ti:
                        txt = ti['decl']
                        if 'value' in ti and ti['value']:
                            txt += ' = {0}'.format(ti['value'])
        # Simply lookup in the file before the use of the variable
        else :
            #If inside a function try first in the function body
            ti = {'type':None}
            if 'meta.function.body' in scope:
                r_func = sublimeutil.expand_to_scope(self.view,'meta.function',region)
                ti = verilog_module.type_info(self.view,self.view.substr(r_func),var_name)
            elif 'meta.task.body' in scope:
                r_func = sublimeutil.expand_to_scope(self.view,'meta.task',region)
                ti = verilog_module.type_info(self.view,self.view.substr(r_func),var_name)
            if not ti['type'] :
                # select whole file until end of current line
                region = self.view.line(region)
                lines = self.view.substr(sublime.Region(0, region.b))
                # Extract type
                ti = verilog_module.type_info(self.view,lines,var_name)
            #if not found check for a definition in base class if we this is an extended class
            if not ti['type'] :
                bti = verilog_module.type_info_from_base(self.view,region,var_name)
                if bti:
                    ti = bti
            elif ti['tag'] == 'decl' :
                is_local = True
            # Type not found in current file ? fallback to sublime index
            if not ti['decl']:
                ti = verilog_module.lookup_type(self.view,var_name)
            if ti:
                txt = ti['decl']
                if 'value' in ti and ti['value']:
                    txt += ' = ' + ti['value']
        # if debug: print('[SV:get_type] Return {0}'.format(ti))
        return txt,ti,colored,is_local

    keywords = ['localparam', 'parameter', 'module', 'interface', 'package', 'class', 'typedef', 'struct', 'union', 'enum', 'packed', 'automatic',
                'local', 'protected', 'public', 'static', 'const', 'virtual', 'function', 'task', 'var', 'modport', 'clocking', 'default', 'extends']

    def color_str(self,s, addLink=False, ti_var=None, last_word=True):
        ss = re.sub(r'<(?!br>)','&lt;',s).split()
        sh = ''
        ti = None
        pos_var = len(ss)-1
        if pos_var>2 and ss[-2] == '=':
            pos_var -= 2
        for i,w in enumerate(ss):
            m = re.match(r'^[A-Za-z_]\w+$',w)
            if '"' in w :
                sh+=re.sub(r'(".*?")',r'<span class="string">\1</span> ',w)
            elif i == len(ss)-1 and last_word:
                if m:
                    if addLink and ti_var and 'fname' in ti_var:
                        fname = '{0}:{1}:{2}'.format(ti_var['fname'][0],ti_var['fname'][1],ti_var['fname'][2])
                        w ='<a href="LINK@{0}" class="entity">{1}</a>'.format(fname,w)
                else:
                    w = re.sub(r'\b((b|d|o)?\d+(\.\d+(ms|us|ns|ps|fs)?)?)\b',r'<span class="numeric">\1</span>',w)
                    w = re.sub(r'(\'h[0-9A-Fa-f]+)\b',r'<span class="numeric">\1</span>',w)
                    w = re.sub(r'(\#|\:|\')',r'<span class="operator">\1</span>',w)
                sh+=w
            elif w in ['input', 'output', 'inout', 'ref']:
                sh+='<span class="support">{0}</span> '.format(w)
            elif w in self.keywords:
                sh+='<span class="keyword">{0}</span> '.format(w)
            elif w in ['wire', 'reg', 'logic', 'int', 'signed', 'unsigned', 'real', 'bit', 'rand', 'void', 'string']:
                sh+='<span class="storage">{0}</span> '.format(w)
            elif '::' in w:
                ws = w.split('::')
                sh+='<span class="support">{0}</span><span class="operator">::</span>'.format(ws[0])
                if addLink:
                    ti = verilog_module.lookup_type(self.view,w)
                    if debug: print('[SV:color_str] user-defined type: word={}::{} => ti={}'.format(ws[0],ws[1],ti));
                if ti and 'fname' in ti:
                    fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                    sh+='<a href="LINK@{0}" class="storage">{1}</a> '.format(fname,ws[1])
                else:
                    sh+='<span class="storage">{0}</span> '.format(ws[1])
            elif '.' in w:
                ws = w.split('.')
                if ws[0] and re.match(r'^[A-Za-z_]\w+$',ws[0]):
                    if addLink:
                        ti = verilog_module.lookup_type(self.view,ws[0])
                    if ti and 'fname' in ti:
                        fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                        sh+='<a href="LINK@{0}" class="storage">{1}</a>'.format(fname,ws[0])
                    else:
                        sh+='<span class="storage">{0}</span>'.format(ws[0])
                    sh+='.<span class="support">{0}</span> '.format(ws[1])
                else :
                    if '#' in ws[0]:
                        sh += re.sub(r'(#)',r'<span class="operator">\1</span> ',ws[0])
                    sh+='.'
                    sh+= re.sub(r'\b(\w+)\b',r'<span class="function">\1</span> ',ws[1],count=1)
            elif '[' in w or '(' in w:
                w = re.sub(r'\b(\d+)\b',r'<span class="numeric">\1</span>',w)
                sh += re.sub(r'(\#|\:)',r'<span class="operator">\1</span>',w) + ' '
            # Color type: typically just before the variable or one word earlier in case of array or parameter
            elif ((i == pos_var-1 or (i>0 and ss[i-1]=='typedef')) and m) or (i == pos_var-2 and ('[' in ss[pos_var-1] or '#' in ss[pos_var-1])) :
                if addLink:
                    ti = verilog_module.lookup_type(self.view,w)
                #if debug: print('[SV:color_str] word={0} => ti={1}'.format(w,ti));
                if ti and 'fname' in ti:
                    fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                    sh+='<a href="LINK@{0}" class="storage">{1}</a> '.format(fname,w)
                else:
                    sh+='<span class="storage">{0}</span> '.format(w)
            elif re.match(r'(\d+\'(b|d|o|h))?\d+',w) :
                sh += re.sub(r'\b((\d+\'(b|d|o|h))?\d+)\b',r'<span class="numeric">\1</span> ',w)
            elif w in ['=','#'] :
                sh += re.sub(r'(=|#)',r'<span class="operator">\1</span> ',w)
            else:
                sh += w + ' '
        return sh,ti

    def on_navigate(self, href):
        href_s = href.split('@')
        if href_s[1]=='__CURRENT__' :
            v = self.view
        else :
            v = self.view.window().find_open_file(href_s[1])
        if v :
            self.view.window().focus_view(v)
            if href_s[0]=='DRIVER':
                goto_driver(v,href_s[2])
            elif href_s[0]=='REFERENCE':
                goto_signal_ref(v,href_s[2])
        else :
            v = self.view.window().open_file(href_s[1],sublime.ENCODED_POSITION)
            global callbacks_on_load
            if href_s[0]=='DRIVER':
                callbacks_on_load[href_s[1]] = lambda v=v, inst_name=href_s[2]: goto_driver(v,inst_name)
            elif href_s[0]=='REFERENCE':
                callbacks_on_load[href_s[1]] = lambda v=v, inst_name=href_s[2]: goto_signal_ref(v,inst_name)


# Manual command to display the popup
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        popup = VerilogTypePopup(self.view)
        popup.show(self.view.sel()[0],-1)

# Event onHover to display the popup
class VerilogShowTypeHover(sublime_plugin.EventListener):
    def on_hover(self, view, point, hover_zone):
        # Popup only on text
        if hover_zone != sublime.HOVER_TEXT:
            return
        # Check file size to optionnaly disable the feature (finding the information can be quite long)
        threshold = view.settings().get('sv.hover_max_size',-1)
        if view.size() > threshold and threshold!=-1 :
            return
        # Only show a popup for systemVerilog, when not in a string of a comment
        scope = view.scope_name(point)
        if 'source.systemverilog' not in scope:
            return
        if any(w in scope for w in ['comment', 'string', 'keyword']):
            return
        popup = VerilogTypePopup(view)
        sublime.set_timeout_async(lambda r=view.word(point), p=point: popup.show(r,p))


###################################################################
# Move cursor to the declaration of the signal currently selected #
class VerilogGotoDeclarationCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region).strip()
        sl = [verilogutil.re_decl + v + r'\b', verilogutil.re_enum + v + r'\b', verilogutil.re_union + v + r'\b', verilogutil.re_inst + v + '\b']
        for s in sl:
            r = self.view.find(s,0)
            if r:
                sublimeutil.move_cursor(self.view,r.b-1)
                return

##############################################################
# Move cursor to the driver of the signal currently selected #
class VerilogGotoDriverCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        signal = self.view.substr(region).strip()
        goto_driver(self.view,signal)



##########################################################
# Move cursor to the begin/end, [], {}, case/endcase ... #
class VerilogGotoBlockBoundary(sublime_plugin.TextCommand):

    def run(self,edit, cmd="move"):
        if len(self.view.sel())==0 : return;
        token_begin = ['begin','(','[','{','module','function','task','class','covergroup','fork','generate','case','interface','clocking']
        token_end   = ['end'  ,')',']','}','endmodule','endfunction','endtask','endclass','endgroup','join','join_none','join_any','endgenerate','endcase','endinterface','endclocking']
        re_token = r'\(|\[|\{|\)|\]|\}|\bbegin\b|\bend\b|'
        re_token += r'\bmodule\b|\bendmodule\b|\bcase\b|\bendcase\b|\bfunction\b|\bendfunction\b|'
        re_token += r'\btask\b|\bendtask\b|\bgenerate\b|\bendgenerate\b|\bclass\b|\bendclass\b|'
        re_token += r'\binterface\b|\bendinterface\b|\bclocking\b|\bendclocking\b|'
        re_token += r'\bcovergroup\b|\bendgroup\b|\bfork\b|\bjoin\b|\bjoin_any\b|\bjoin_none\b'
        sel = self.view.sel()[0]
        tl = []
        rl = self.view.find_all(re_token,0,r'$0',tl)
        i = 0
        while i<len(rl) and rl[i].a < sel.b:
            i=i+1
        if i==len(rl):
            return
        si = i-1 # start index
        ei = i # end index
        cnt = 0
        # Search for token start before pt, ignoring pairs and token inside comment or string
        scope = self.view.scope_name(rl[si].a)
        while si>0 and (tl[si] not in token_begin or cnt>0 or 'comment' in scope or 'string' in scope):
            if 'comment' not in scope and 'string' not in scope:
                if tl[si] in token_end:
                    cnt = cnt + 1
                else:
                    cnt = cnt - 1
            si = si - 1
            scope = self.view.scope_name(rl[si].a)
        if cnt!=0:
            # print('[SV.GotoBlockBoundary] Pairs not balanced toward start')
            return
        # Search for token end after pt, ignoring pairs and token inside comment or string
        scope = self.view.scope_name(rl[ei].a)
        while ei<len(tl) and (tl[ei] not in token_end or cnt>0 or 'comment' in scope or 'string' in scope):
            if 'comment' not in scope and 'string' not in scope:
                if tl[ei] in token_begin:
                    cnt = cnt + 1
                else:
                    cnt = cnt - 1
            ei = ei + 1
            if ei==len(tl):
                # print('[SV.GotoBlockBoundary] Pairs not balanced toward end')
                return
            scope = self.view.scope_name(rl[ei].a)
        # Select text
        # print('[SV.GotoBlockBoundary] Cursor at {0} - surrounded by "{1}" ({2}=>{3}) and "{4}" ({5}=>{6})'.format(pt,tl[si],rl[si].a,self.view.rowcol(rl[si].a),tl[ei],rl[ei].a,self.view.rowcol(rl[ei].a)))
        if cmd=='select':
            self.view.sel().clear()
            if sel.a != rl[si].b or sel.b != rl[ei].a :
                self.view.sel().add(sublime.Region(rl[si].b,rl[ei].a))
            else :
                self.view.sel().add(sublime.Region(rl[si].a,rl[ei].b))
        else :
            # Move cursor to the end token if not already at the end. Otherwise move it to the start one
            if sel.b<rl[ei].a:
                pos = rl[ei].a
            else:
                pos = rl[si].b
            sublimeutil.move_cursor(self.view,pos)

############################################################################
# Helper function to retrieve current module name based on cursor position #

def getModuleName(view):
    r = view.sel()[0]
    # Empty selection ? get current module name
    if r.empty():
        p = r'(?s)^[ \t]*(module|interface)\s+(\w+\b)'
        nameList = []
        rList = view.find_all(p,0,r'\2',nameList)
        name = ''
        if rList:
            name = nameList[0]
            # Handle case where there is multiple class in a file
            # and select the one closest to the cursor
            for (rf,n) in zip(rList,nameList):
                if rf.a < r.a:
                    name = n
                else:
                    break
    else:
        name = view.substr(r)
    # print(name)
    return name

def goto_driver(view,signal):
    signal_word = r'\b'+signal+r'\b'
    # look for an input or an interface of the current module, and for an assignement
    sl = [r'input\s+(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:]*\s+)?(\[[\w\:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?' + signal + r'\b']
    sl.append(r'^\s*\w+\.\w+\s+' + signal + r'\b')
    sl.append(r'\b' + signal + r'\b(\[[^\]]*\])*\s*<?\=[^\=]')
    for s in sl:
        r = view.find(s,0)
        # print('searching ' + s + ' => ' + str(r))
        if r:
            # print("Found input at " + str(r) + ': ' + view.substr(view.line(r)))
            sublimeutil.move_cursor(view,r.a)
            return
    # look for a connection explicit, implicit or by position
    sl = [r'\.(\w+)\s*\(\s*'+signal+r'\b' , r'(\.\*)', r'(\(|,)\s*'+signal+r'\b\s*(,|\)\s*;)']
    for k,s in enumerate(sl):
        pl = []
        rl = view.find_all(s,0,r'$1',pl)
        # print('searching ' + s + ' => ' + str(rl))
        for i,r in enumerate(rl):
            # print('Found in line ' + view.substr(view.line(r)))
            # print('Scope for ' + str(r) + ' = ' + view.scope_name(r.a))
            if 'meta.module.inst' in view.scope_name(r.a) :
                rm = sublimeutil.expand_to_scope(view,'meta.module.inst',r)
                txt = verilogutil.clean_comment(view.substr(rm))
                # Parse module definition
                mname = re.findall(r'\w+',txt)[0]
                filelist = view.window().lookup_symbol_in_index(mname)
                if not filelist:
                    return
                for f in filelist:
                    fname = sublimeutil.normalize_fname(f[0])
                    mi = verilogutil.parse_module_file(fname,mname)
                    if mi:
                        break
                if mi:
                    op = r'^(output\s+.*|\w+\.\w+\s+)'
                    # Output port string to search
                    portname = ''
                    if k==1: #Explicit connection
                        portname = signal
                    elif k==0: #implicit connection
                        portname = pl[i]
                    elif k==2 : #connection by position
                        for j,l in enumerate(txt.split(',')) :
                            if signal in l:
                                dl = [x['decl'] for x in mi['port']]
                                if re.search(op,dl[j]) :
                                    r_v = view.find(signal_word,rm.a)
                                    if r_v and r_v.b<=rm.b:
                                        sublimeutil.move_cursor(view,r_v.a)
                                    else:
                                        sublimeutil.move_cursor(view,r.a)
                                    return
                    if portname != '' :
                        op += portname+r'\b'
                        for x in mi['port']:
                            m = re.search(op,x['decl'])
                            if m:
                                r_v = view.find(signal_word,rm.a)
                                if r_v and r_v.b<=rm.b:
                                    sublimeutil.move_cursor(view,r_v.a)
                                else:
                                    sublimeutil.move_cursor(view,r.a)
                                return
    # Everything failed
    sublime.status_message("Could not find driver of " + signal)

def goto_signal_ref(view,signal):
    lr = view.find_all(r'\b{}\b'.format(signal))
    refs = { 'txt':[], 'row':[], 'point':[] }
    for r in lr:
        scope = view.scope_name(r.b)
        if 'comment' in scope or 'meta.module' in scope :
            continue
        row,col = view.rowcol(r.b)
        if row not in refs['row']:
            line = view.substr(view.line(r.b)).strip()
            if re.search(r'\b{}\b\s*<?=(?!=)',line) :
                continue
            refs['txt'].append(line)
            refs['row'].append(row)
            refs['point'].append(r.b)
    if len(refs['row']) > 1 :
        view.window().show_quick_panel(refs['txt'],
            on_select    = lambda x:sublimeutil.move_cursor(view,refs['point'][x]),
            on_highlight = lambda x:sublimeutil.move_cursor(view,refs['point'][x]))
    elif len(refs['row']) == 1 :
        sublimeutil.move_cursor(view,refs['point'][0])

def goto_first_occurence(view,name):
    r = sublime.Region(0)
    max_rb = view.size()
    while r.b < max_rb :
        r = view.find(r'\b{}\b'.format(name),r.b)
        # print('Found "{}" at {} (max={})'.format(name,r,max_rb))
        if not r:
            return
        if 'comment' not in view.scope_name(r.a):
            break;
    view.window().focus_view(view)
    sublimeutil.move_cursor(view,r.a)

######################################################################################
# Create a new buffer showing the hierarchy (sub-module instances) of current module #
hierarchyInfo = {'dict':{}, 'view':None,'fname':''}

class VerilogShowHierarchyCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        mname = getModuleName(self.view)
        txt = self.view.substr(sublime.Region(0, self.view.size()))
        mi = verilogutil.parse_module(txt,mname,True)
        if not mi:
            print('[VerilogShowHierarchyCommand] Not inside a module !')
            return
        sublime.status_message("Show Hierarchy can take some time, please wait ...")
        sublime.set_timeout_async(lambda mi=mi, w=self.view.window(), txt=txt: self.showHierarchy(mi,w,txt))

    def showHierarchy(self,mi,w,txt):
        # Save info in global for later access
        global hierarchyInfo
        hierarchyInfo['view'] = self.view
        hierarchyInfo['fname'] = self.view.file_name()

        # Create Dictionnary where each type is associated with a list of tuple (instance type, instance name)
        self.d = {}
        top_level = mi['name']
        # Extract Symbol position
        for x in self.view.symbols() :
            if x[1] == top_level:
                row,col = self.view.rowcol(x[0].a)
                hierarchyInfo['fname'] += ':{}:{}'.format(row,col+2)
                break
        self.d[mi['name']] = [(x['type'],x['name']) for x in mi['inst']]
        self.unresolved = []
        li = [x['type'] for x in mi['inst']]
        while li :
            # print('Loop on list with {1} elements : {2}'.format(len(li),li))
            li_next = []
            for i in li:
                if i not in self.d.keys() and i not in self.unresolved:
                    filelist = w.lookup_symbol_in_index(i)
                    if filelist:
                        for f in filelist:
                            fname = sublimeutil.normalize_fname(f[0])
                            mi = verilogutil.parse_module_file(fname,i,True)
                            if mi:
                                hierarchyInfo['dict'][mi['name']] = '{}:{}:{}'.format(fname,f[2][0],f[2][1])
                                break
                    # Not in project ? try in current file
                    else :
                        mi = verilogutil.parse_module(txt,i,True)
                        if mi:
                            hierarchyInfo['dict'][mi['name']] = self.view.file_name()
                    if mi:
                        li_next += [x['type'] for x in mi['inst']]
                        if mi['type'] not in ['interface']:
                            self.d[i] = [(x['type'],x['name']) for x in mi['inst']]
                    else:
                        self.unresolved.append(i)
            li = list(set(li_next))
        txt = top_level + '\n'
        txt += self.printSubmodule(top_level,1)

        nw = self.view.settings().get('sv.hierarchy_new_window',False)
        if nw:
            sublime.run_command('new_window')
            w = sublime.active_window()

        v = w.new_file()
        v.settings().set("tab_size", 2)
        v.set_name(top_level + ' Hierarchy')
        v.set_syntax_file('Packages/SystemVerilog/Find Results SV.hidden-tmLanguage')
        v.set_scratch(True)
        v.run_command('insert_snippet',{'contents':str(txt)})

    def printSubmodule(self,name,lvl):
        txt = ''
        if name in self.d:
            # print('printSubmodule ' + str(self.d[name]))
            for x in self.d[name]:
                txt += '  '*lvl
                if x[0] in self.d :
                    txt += '+ {name}    ({type})\n'.format(name=x[1],type=x[0])
                    if lvl<20 :
                        txt += self.printSubmodule(x[0],lvl+1)
                else:
                    ustr = '  [U]' if x[0] in self.unresolved else ''
                    txt += '- {name}    ({type}){unresolved}\n'.format(name=x[1],type=x[0],unresolved=ustr)
        return txt

# Navigate within the hierarchy
class VerilogHierarchyGotoDefinitionCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        global hierarchyInfo
        r = self.view.sel()[0]
        if r.empty() :
            r = self.view.word(r)
        scope = self.view.scope_name(r.a)
        fname = ''
        inst_name = ''
        # Not in the proper file ? use standard goto_definition to
        if 'text.result-systemverilog' not in scope:
            self.view.window().run_command('goto_definition')
            return
        if 'entity.name' in scope:
            l = self.view.substr(self.view.line(r))
            indent = (len(l) - len(l.lstrip()))-2
            if indent<0:
                print('[SV.navigation] Hierarchy buffer corrupted : Invalid position for an instance !')
                return
            elif indent == 0:
                fname = hierarchyInfo['fname']
            else:
                w = ''
                # find module parent name
                txt = self.view.substr(sublime.Region(0,r.a))
                m = re.findall(r'^{}\+ \w+\s+\((\w+)\)'.format(' '*indent),txt,re.MULTILINE)
                if m:
                    inst_name = self.view.substr(r)
                    if m[-1] in hierarchyInfo['dict']:
                        fname = hierarchyInfo['dict'][m[-1]]
        elif 'storage.name' in scope:
            w = self.view.substr(r)
            if w in hierarchyInfo['dict']:
                fname = hierarchyInfo['dict'][w]
        elif 'keyword.module' in scope:
            fname = hierarchyInfo['fname']

        if fname:
            if not inst_name:
                hierarchyInfo['view'].window().open_file(fname,sublime.ENCODED_POSITION)
            else:
                m = re.match(r'(.+)\:(\d+)\:(\d+)',fname)
                fname_short = fname if not m else m.group(1)
                v = hierarchyInfo['view'].window().find_open_file(fname_short)
                if v :
                    hierarchyInfo['view'].window().focus_view(v)
                    self.goto_symb(v,inst_name)
                else :
                    v = hierarchyInfo['view'].window().open_file(fname,sublime.ENCODED_POSITION)
                    global callbacks_on_load
                    callbacks_on_load[fname_short] = lambda v=v, inst_name=inst_name: self.goto_symb(v,inst_name)

    def goto_symb(self,v,inst_name):
        row=-1
        for x in v.symbols() :
            if x[1] == inst_name:
                row,col = v.rowcol(x[0].a)
                break
        if row>=0:
            sublimeutil.move_cursor(v,v.text_point(row,col))

######################################################################################
# Create a new buffer showing the class hierarchy (sub-class instances) of current class #

PHANTOM_TEMPLATE = """
<body id="sv-navbar">
<style>
    html, body {{
        margin: 0;
        padding: 0;
        background-color: transparent;
    }}
    a {{
        text-decoration: none;
        color: {1};
    }}
    .content {{color: {1};}}
</style>
<span class="content">{0}</span>
</body>
"""


def getObjList(view):
    r = view.sel()[0]
    p = r'(?s)^[ \t]*(?:virtual\s+)?(class|module|interface)\s+(\w+\b)'
    nameList = []
    r = view.find_all(p,0,r'\1 \2',nameList)
    nl = []
    for (r,n) in zip(r,nameList):
        if 'comment' not in view.scope_name(r.a):
            nl.append(n)
    return nl

class VerilogShowNavbarCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        objects = getObjList(self.view)
        if not objects:
            # print('[SV:NavBar] Not inside a module/interface/class !')
            return
        enable = self.view.settings().get('sv.navbar_update',15)
        if objects[0][0] == 'class' and (enable & 1) == 0:
            return
        elif objects[0][0]== 'module' and (enable & 1) == 0:
            return
        elif (enable & 4) == 0:
            return
        sublime.set_timeout_async(lambda objects=objects: self.showHierarchy(objects))

    def showHierarchy(self,objects):
        # Save info in global for later access
        info = {'view':None,'fname':''}
        info['view'] = self.view
        info['fname'] = self.view.file_name()

        global navBar
        w = sublime.active_window()
        wid = w.id()
        navbar_flag = w.settings().get('navbar-hdl-shared', 0)
        # print('navbar_flag = {}'.format(navbar_flag))
        if wid not in navBar :
            l = w.get_layout()
            nb_col = len(l['cols'])
            if navbar_flag != 0:
                if nb_col < 2:
                    navbar_flag = 0
                else :
                    gid = len(l['cells'])-1
                    vl = w.views_in_group(gid)
                    if len(vl) == 1:
                        if not vl[0].name().endswith(' Hierarchy') :
                            navbar_flag = 0
                    else :
                        navbar_flag = 0
            if navbar_flag == 0:
                l['cols'].append(1.0)
                width = self.view.settings().get('sv.navbar_width',0.2)
                delta = width / (nb_col-1)
                for i in range(1,nb_col) :
                    l['cols'][i] -= i * delta
                l['cells'].append([nb_col-1,0,nb_col,1])
                w.set_layout(l)
                w.focus_group(len(l['cells'])-1)
                navBarView = w.new_file()
                navBarView.settings().set("tab_size", 2)
            else :
                l = w.get_layout()
                w.focus_group(len(l['cells'])-1)
                group_id = len(l['cells'])-1
                w.focus_group(group_id)
                navBarView = w.active_view_in_group(group_id)
                navBarView.run_command("select_all")
                navBarView.run_command("right_delete")
            navBarView.set_scratch(True)
            navBar[wid] = {'view':navBarView, 'info':info, 'settings':{}, 'vhdl_on': False}
            navBar[wid]['settings']['update'            ] = self.view.settings().get('sv.navbar_update',15)
            navBar[wid]['settings']['show_module_port'  ] = self.view.settings().get('sv.navbar_show_module_port',True)
            navBar[wid]['settings']['show_module_signal'] = self.view.settings().get('sv.navbar_show_module_signal',False)
            navBar[wid]['settings']['show_interface_cb' ] = self.view.settings().get('sv.navbar_show_interface_cb',False)
        else :
            navBar[wid]['view'].run_command("select_all")
            navBar[wid]['view'].run_command("right_delete")
            navBar[wid]['info'] = info

        if 'systemverilog' not in navBar[wid]['view'].scope_name(0):
            navBar[wid]['view'].set_syntax_file('Packages/SystemVerilog/navbar.sublime-syntax')
        w.settings().set('navbar-hdl-shared', navbar_flag | 1)

        navBar[wid]['childless'] = ['logic','bit','byte','int','event', 'string','real', 'semaphore', 'process', 'time']


        ftxt = self.view.substr(sublime.Region(0, self.view.size()))
        txt = ''
        for i,o in enumerate(objects) :
            t,_,name = o.partition(' ')
            # print('[SV:NavBar] Extracting info for {} {} ({})'.format(t,name,o))
            if t == 'class' :
                mi = verilogutil.parse_class(ftxt,name)
            elif t== 'module':
                mi = verilogutil.parse_module(ftxt,name)
            else:
                mi = verilogutil.parse_module(ftxt,name)
            if not mi:
                print('[SV:NavBar] Unable to parse "{}" !'.format(name))
                return

            # Create content
            top_level = mi['name']
            if mi['type'] == 'class' :
                txt_ = re.sub(r'class\s+','',mi['decl'])
                txt_ = re.sub(r'\s+extends\b.+','',txt_)
                txt_ = re.sub(r'\n','',txt_)
                txt += re.sub(r'(parameter|localparam)\s+','',txt_)
                txt += '\n'
                if mi['extend']:
                    txt += '  {}\n'.format(mi['extend'])
            else :
                txt += '{}\n'.format(top_level)
            txt += '-'*len(top_level) + '\n'
            txt += self.printContent(1,mi,navBar[wid])

            if i< len(objects) - 1:
                txt += '\n{}\n\n'.format('='*len(top_level))

        navBar[wid]['view'].set_name(top_level + ' Hierarchy')
        navBar[wid]['view'].run_command('insert_snippet',{'contents': '$x', 'x':txt})

        # Add phantoms
        self.build_phantoms(wid)

        # Fold functions arguments
        navBar[wid]['view'].run_command("fold_by_level", {"level": 2})
        # Ensure focus is at beginning of file
        sublimeutil.move_cursor(navBar[wid]['view'],0)

    def printContent(self,lvl,ti, nb):
        txt = ''
        if 'port' in ti and ti['port'] and ((nb['settings']['show_module_port'] and lvl==1) or ti['type']!='module'):
            txt += '{}Ports:\n'.format('  '*(lvl-1))
            for p in ti['port'] :
                txt += '{}* {}\n'.format('  '*lvl,p['decl'])
        if 'signal' in ti and ti['signal'] and ((nb['settings']['show_module_signal'] and lvl==1) or ti['type']!='module'):
            txt += '{}Signals:\n'.format('  '*(lvl-1))
            for p in ti['signal'] :
                txt += '{}* {}\n'.format('  '*lvl,p['decl'])
        if 'inst' in ti and ti['inst']:
            if lvl==1 and (nb['settings']['show_module_port'] or nb['settings']['show_module_signal']):
                txt += '{}Instances:\n'.format('  '*(lvl-1))
            else :
                lvl -= 1
            for inst in ti['inst']:
                if inst['type'] in nb['childless']:
                    symb = u'\u180E'
                else :
                    symb = ''
                txt += '{}{}{name} ({type})\n'.format('  '*lvl,symb,name=inst['name'],type=inst['type'])
        if 'member' in ti and ti['member'] :
            txt += '{}Members:\n'.format('  '*(lvl-1))
            for c in ti['member']:
                # Ignore typedef
                if c['tag'] == 'typedef' or c['decl'].startswith('typedef'):
                    continue
                # print(c)
                t = c['type']
                if 'bw' in c and c['bw']:
                    t += ' ' + c['bw']
                if ' ' in t or t in nb['childless']:
                    symb = u'\u180E'
                else :
                    symb = ''
                dim = '' if 'array' not in c or not c['array'] else ' {}'.format(c['array_dim'])
                txt += '{}{}{name}{dim} ({type})\n'.format('  '*lvl,symb,name=c['name'],type=t, dim=dim)
        if 'function' in ti and ti['function'] :
            txt += '{}Methods:\n'.format( '  '*(lvl-1))
            for f in ti['function']:
                txt += '  '*lvl
                txt += '{name} ({type})\n'.format(name=f['name'],type=f['type'])
                if f['port'] :
                    for p in f['port'] :
                        txt += '{}* {}\n'.format('  '*(lvl+1),p['decl'])
        if 'modport' in ti and ti['modport']:
            txt += '{}Modports:\n'.format('  '*(lvl-1))
            for p in ti['modport'] :
                txt += '{}* {}\n'.format('  '*lvl,p['name'])
        # if 'clocking' in ti and ti['clocking']:
        #     print(ti['clocking'])
        return txt

    def getBaseClass(self,name):
        (name_, *_) = name.split(maxsplit=1)
        filelist = sublime.active_window().lookup_symbol_in_index(name_)
        if filelist:
            re_str = r'class\s+' + name_ + r'\b([^;]+);'
            for fname, display_fname, rowcol in filelist:
                fname = sublimeutil.normalize_fname(fname)
                with open(fname) as f:
                    flines = f.read()
                    m = re.search(re_str,flines,flags=re.MULTILINE)
                    if m :
                        mbc = re.search(r'\bextends\s+([^;]+)',m.group(1),flags=re.MULTILINE)
                        if mbc :
                            return mbc.group(1)
                        else:
                            return None
        return None

    def build_phantoms(self,wid):
        view = navBar[wid]['view']
        # Clear exiting phantoms if nay
        if 'phantomSet' in navBar[wid] :
            navBar[wid]['view'].erase_phantoms('sv-navbar')
        # Phantoms for base type
        regions = view.find_by_selector('storage.name.base-type.hierarchy-systemverilog')
        phantoms = []
        pid = 0
        for r in regions :
            name = view.substr(r)
            ilc = view.indentation_level(r.a)
            pnl = view.line(r).b+1
            iln = view.indentation_level(pnl)
            # print('indent level for basetype {} = {} {}'.format(name,ilc,iln))
            if ilc>=iln :
                content = '<a href="extend:{}:{}">+</a>'.format(name,r.a)
            elif view.is_folded(sublime.Region(pnl)) :
                content = '<a href="unfold:{}:0">+</a>'.format(r.a)
            else :
                content = '<a href="fold:{}:0">-</a>'.format(r.a)
            phantoms.append(sublime.Phantom(
                region=r,
                content=PHANTOM_TEMPLATE.format(content,colors['operator']),
                layout=sublime.LAYOUT_INLINE,
                on_navigate=self.on_navigate)
            )
            pid += 1
        # Phantoms for members
        regions = view.find_by_selector('storage.name.type.userdefined.hierarchy-systemverilog')
        for r in regions :
            name = view.substr(r)
            ilc = view.indentation_level(r.a)
            pnl = view.line(r).b+1
            iln = view.indentation_level(pnl)
            # print('Point {} ({}) : indent = {} vs {}, folded = {}'.format(pnl,view.rowcol(pnl),iln,ilc,view.is_folded(sublime.Region(pnl))))
            # print('indent level for member {} = {} {}'.format(name,ilc,iln))
            if name in navBar[wid]['childless'] :
                content = '<a>-</a>'
            elif ilc>=iln :
                content = '<a href="type:{}:{}:{}:{}">+</a>'.format(name,r.a,ilc,pid)
            elif view.is_folded(sublime.Region(pnl)) :
                content = '<a href="unfold:{}:{}">+</a>'.format(r.a,pid)
            else :
                content = '<a href="fold:{}:{}">-</a>'.format(r.a,pid)
            r = sublime.Region(view.line(r).a + ilc*2)
            phantoms.append(sublime.Phantom(
                region = r,
                content=PHANTOM_TEMPLATE.format(content,colors['operator']),
                layout=sublime.LAYOUT_INLINE,
                on_navigate=self.on_navigate)
            )
            pid += 1
        regions = view.find_by_selector('meta.annotation.marker')
        for r in regions :
            phantoms.append(sublime.Phantom(
                region = r,
                content=PHANTOM_TEMPLATE.format('-',colors['operator']),
                layout=sublime.LAYOUT_INLINE)
            )
        if len(phantoms)>0:
            navBar[wid]['phantomSet'] = sublime.PhantomSet(navBar[wid]['view'], "sv-navbar")
            navBar[wid]['phantom'] = phantoms
            navBar[wid]['phantomSet'].update(phantoms)

    def change_phantom(self,wid,v,pid,content):
        v.erase_phantoms('sv-navbar')
        navBar[wid]['phantomSet'] = sublime.PhantomSet(v, "sv-navbar")
        navBar[wid]['phantom'][pid].content = PHANTOM_TEMPLATE.format(content,colors['operator'])
        navBar[wid]['phantomSet'].update(navBar[wid]['phantom'])

    def on_navigate(self,href):
        global navBar
        href_s = href.split(':')
        w = sublime.active_window()
        wid = w.id()
        view = navBar[wid]['info']['view']
        v =  navBar[wid]['view']
        # print('[SV.Navbar] on_navigate = {}\n\tChildless = {}'.format(href_s,navBar[wid]['childless']))
        if href_s[0]=="extend" :
            name = href_s[1]
            txt = ''
            lvl = 2
            while True:
                bc = self.getBaseClass(name)
                if bc is None or len(bc) == 0:
                    break;
                name = bc
                txt += '  ' * lvl
                txt += '- {} \n'.format(name)
                lvl += 1
            r = v.line(sublime.Region(int(href_s[2])))
            v.sel().clear()
            v.sel().add(r.b+1)
            v.run_command('insert_snippet',{'contents': '$x', 'x':txt})
            self.build_phantoms(wid)
        elif href_s[0]=="type" :
            if href_s[1] in navBar[wid]['childless'] :
                self.change_phantom(wid,v,int(href_s[4]),'<a>-</a>')
                return
            ti = verilog_module.lookup_type(view,href_s[1])
            # print(ti)
            if not ti or 'type' not in ti:
                navBar[wid]['childless'].append(href_s[1])
                self.change_phantom(wid,v,int(href_s[4]),'<a>-</a>')
                print('Type {} not found: {}'.format(href_s[1],ti))
                return
            if ti['type'] == 'class':
                if 'fname' in ti :
                    ci = verilogutil.parse_class_file(ti['fname'][0],ti['name'])
                    txt = self.printContent(2,ci,navBar[wid])
                    if txt:
                        r = self.insert_text_next_line(v,int(href_s[2]),txt)
                        self.build_phantoms(wid)
                        # Fold methods if any
                        if ci['function'] :
                            self.fold_methods(v,r)
                    else :
                        navBar[wid]['childless'].append(ti['name'])
                        self.change_phantom(wid,v,int(href_s[4]),'<a>-</a>')
            elif ti['type'] == 'enum':
                txt = ''
                for val in verilogutil.get_enum_values(ti['decl']):
                    txt += '    * {}\n'.format(val)
                if txt:
                    self.insert_text_next_line(v,int(href_s[2]),txt)
                    self.build_phantoms(wid)
            elif ti['type'] == 'struct':
                # print(ti['decl'])
                m = re.search(r'\{(.*)\}',ti['decl'])
                if m:
                    t = ''
                    for x in m.group(1).split(';'):
                        f = x.strip()
                        if f:
                            t += '    * {}\n'.format(f)
                    self.insert_text_next_line(v,int(href_s[2]),t)
                    self.build_phantoms(wid)
                return
            elif ti['type'] == 'interface' or ti['type'] == 'module' :
                if 'fname' in ti :
                    ci = verilogutil.parse_module_file(ti['fname'][0],ti['name'])
                    txt = self.printContent(2,ci,navBar[wid])
                    if txt:
                        r = self.insert_text_next_line(v,int(href_s[2]),txt)
                        self.build_phantoms(wid)
                    else :
                        navBar[wid]['childless'].append(ti['name'])
                        self.change_phantom(wid,v,int(href_s[4]),'<a>-</a>')
            else :
                # print('Unsupported Type {} not found: {}'.format(href_s[1],ti))
                return
        elif href_s[0]=="fold" :
            r_start = int(href_s[1])
            s = sublime.Region(v.line(r_start).b+1)
            s = v.indented_region(s.b)
            if not s.empty():
                s.a -= 1
                s.b -= 1
                v.fold(s)
            pid = int(href_s[2])
            t = '<a href="unfold:{}:{}">+</a>'.format(r_start,pid)
            self.change_phantom(wid,v,pid,t)
        elif href_s[0]=="unfold" :
            r_start = int(href_s[1])
            s = sublime.Region(v.line(r_start).b+1)
            v.unfold(s)
            pid = int(href_s[2])
            t = '<a href="fold:{}:{}">-</a>'.format(r_start,pid)
            self.change_phantom(wid,v,pid,t)
            self.fold_methods(v,s)

    def insert_text_next_line(self, v, r, txt):
        r = v.line(sublime.Region(r))
        v.sel().clear()
        v.sel().add(r.b)
        # Workaround weird auto-indentation behavior of insert_snippet
        v.run_command('insert_snippet', {'contents': '\n'})
        v.run_command('insert_snippet', {'contents': '$x', 'x':txt[:-1]})
        return r

    def fold_methods(self, v, r_start) :
        folds = []
        rs = v.indented_region(r_start.b)
        r = v.find("Methods:",r_start.b)
        ilm = v.indentation_level(r.a)+1
        if r.a >= rs.b:
            return
        while(True) :
            # Go next line
            r = sublime.Region(v.line(r).b+1)
            il = v.indentation_level(r.a)
            if il < ilm or r.b >= rs.b:
                break
            else :
                s = sublime.Region(v.line(r).b+1)
                il = v.indentation_level(s.a)
                if il < ilm or r.b >= rs.b:
                    break
                elif il > ilm :
                    s = v.indented_region(s.b)
                    if not s.empty():
                        r = s
                        s.a -= 1
                        s.b -= 1
                        folds.append(s)
        v.fold(folds)

# Toggle Open/close navigation Bar
class VerilogToggleNavbarCommand(sublime_plugin.WindowCommand):

    def run(self, cmd='toggle'):
        global navBar
        w = self.window
        wid = w.id()
        av = w.active_view()
        # print('[SV] : wid = {}, navbar={}, cmd={}'.format(wid,navBar.keys(),cmd))
        if wid in navBar and cmd != 'open':
            nv = navBar[wid]['view']
            if av is None or av == nv :
                av = navBar[wid]['info']['view']
            w.settings().set('navbar-hdl-shared', 0)
            # Close the navBar view
            if wid not in navBar :
                return
            del navBar[wid]
            sublime.active_window().run_command("vhdl_toggle_navbar",{'cmd':'disable'})
            if cmd == 'disable' :
                return
            if cmd == 'toggle' :
                # print('[SV] Focus on view {}'.format(nv.id()))
                self.window.focus_view(nv)
                nv.set_scratch(True)
                self.window.run_command("close_file")

            # Remove the extra group in which the navbar was created
            l = self.window.get_layout()
            width = l['cols'][-1] - l['cols'][-2]
            l['cols'].pop()
            nb_col = len(l['cols'])
            if nb_col == 1:
                return
            delta = width / (nb_col-1)
            for i in range(1,nb_col) :
                l['cols'][i] += i*delta
            l['cells'].pop()
            self.window.set_layout(l)
            # Focus back on initial view
            # print('[SV] Focus back on view {}'.format(av.id()))
            self.window.focus_view(av)
        elif self.window.settings().get('navbar-hdl-shared', 0) != 0 and cmd != 'open':
            self.window.settings().set('navbar-hdl-shared', 0)
            sublime.active_window().run_command("vhdl_toggle_navbar",{'cmd':'close'})
        elif cmd in ['open','toggle'] and av :
            if 'vhdl' in  av.scope_name(0):
                av.run_command("vhdl_show_navbar")
            else :
                av.run_command("verilog_show_navbar")

# Update the navigation bar
class VerilogUpdateNavbarCommand(sublime_plugin.EventListener):

    def on_activated_async(self,view):
        w = sublime.active_window()
        wid = w.id()
        if wid not in navBar:
            return;
        scope =  view.scope_name(0)
        # print('[SV] : fnamer={} - {} ({}), update={}, scope={}, navbar_flag={}'.format(navBar[wid]['info']['fname'],view.file_name(),view.id(),navBar[wid]['settings']['update'],scope,w.settings().get('navbar-hdl-shared', 0)))
        if navBar[wid]['info']['fname'] == view.file_name():
            if 'verilog' in navBar[wid]['view'].scope_name(0):
                return
            elif 'source.systemverilog' in scope :
                view.run_command("verilog_show_navbar")
        if navBar[wid]['settings']['update'] == 0:
            return
        if 'source.systemverilog' in scope:
            view.run_command("verilog_show_navbar")
        if 'source.vhdl' in scope:
            navbar_flag = w.settings().get('navbar-hdl-shared', 0)
            if navbar_flag & 2 == 0 :
                view.run_command("vhdl_show_navbar")

# Update the navigation bar
class VerilogToggleLockNavbarCommand(sublime_plugin.WindowCommand):

    def run(self):
        global navBar
        wid = self.window.id()
        if wid in navBar :
            if navBar[wid]['settings']['update'] == 0:
                navBar[wid]['settings']['update'] = navBar[wid]['view'].settings().get('sv.navbar_update',15)
                # If default is 0 unlock fully
                if navBar[wid]['settings']['update'] == 0:
                    navBar[wid]['settings']['update'] = 15
                self.window.status_message('SystemVerilog NavBar unlocked ({})'.format(navBar[wid]['settings']['update']))
            else :
                navBar[wid]['settings']['update'] = 0
                self.window.status_message('SystemVerilog NavBar locked ')


class VerilogHandleNavbarCommand(sublime_plugin.ViewEventListener):

    @classmethod
    def is_applicable(cls, settings):
        return settings.get('syntax') == 'Packages/SystemVerilog/navbar.sublime-syntax'

    def on_close(self):
        sublime.active_window().run_command("verilog_toggle_navbar",{'cmd':'close'})

    def on_text_command(self, command_name, args):
        # Detect double click
        double_click = command_name == 'drag_select' and 'by' in args and args['by'] == 'words'
        if not double_click:
            return
        s = self.view.sel()[0]
        scope = self.view.scope_name(s.a)
        region = self.view.word(s)
        name = self.view.substr(region)
        if name.startswith(u'\u180E'):
            name = name[1:]
        w = sublime.active_window()
        wid = w.id()
        v = navBar[wid]['info']['view']
        # print('s = {}, r={} scope="{}"'.format(s,region,scope))
        if 'base-type' in scope or 'userdefined' in scope:
            sublimeutil.goto_index_symbol(v,name)
        elif 'entity.name.method' in scope:
            cname = navbar_get_class(self.view,s)
            if cname :
                filelist = w.lookup_symbol_in_index(cname)
                if filelist :
                    sublimeutil.goto_symbol_in_file(v,name,sublimeutil.normalize_fname(filelist[0][0]),0)
            else :
                r,n = navbar_get_top(self.view,s.a)
                sublimeutil.goto_symbol_in_file(v,name,v.file_name(),r.b)
        elif 'entity.name.hierarchy-systemverilog' or 'source.name.hierarchy-systemverilog' in scope:
            cname = navbar_get_class(self.view,s)
            if cname :
                # print('[SV.Navbar] Class for {} is {}'.format(name,cname))
                if cname in ['function','task']:
                    return
                v,fname = sublimeutil.goto_index_symbol(v,cname)
                if v:
                    # print('GotoIndexSymbols -> {} ({})'.format(fname,v.id()))
                    if fname:
                        global callbacks_on_load
                        callbacks_on_load[fname] = lambda v=v, name=name: goto_first_occurence(v,name)
                        return
                    else :
                        goto_first_occurence(v,name)
            else :
                # print('[SV.Navbar] Navigate to first occurence of {}'.format(name))
                goto_first_occurence(v,name)

def navbar_get_class(view,r):
    il = view.indentation_level(r.a)
    # Not local member : find to which class this belongs
    if il > 1 :
        r = view.indented_region(r.a)
        p = view.find_by_class(r.a,False,sublime.CLASS_WORD_START)
        # If going up one level gives a keyword, it means we need to go up another level
        scope = view.scope_name(p)
        if 'keyword' in scope:
            r = view.indented_region(p)
            p = view.find_by_class(r.a,False,sublime.CLASS_WORD_START)
        cname = view.substr(view.word(p))
    else :
        cname = ''
    return cname

def navbar_get_top(view,pt):
    name = ''
    regions = view.find_by_selector('keyword.top-level.hierarchy-systemverilog')
    if not regions:
        return ''
    rs = regions[0]
    for r in regions:
        if pt < r.a :
            break
        name = view.substr(r)
        rs = r
    return rs,name


###########################################################
# Find all instances of current module or selected module #
class VerilogFindInstanceCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        mname = getModuleName(self.view)
        sublime.status_message("Find Instance can take some time, please wait ...")
        sublime.set_timeout_async(lambda x=mname: self.findInstance(x))

    def findInstance(self, mname):
        projname = sublime.active_window().project_file_name()
        if projname not in verilog_module.list_module_files:
            verilog_module.VerilogModuleInstCommand.get_list_file(self,projname,None)
        inst_dict = {}
        cnt = 0
        re_str = r'^(\s*'+mname+r'\s+(#\s*\(.*\)\s*)?(\w+).*$)'
        p = re.compile(re_str,re.MULTILINE)
        for fn in verilog_module.list_module_files[projname]:
            with open(fn) as f:
                txt = f.read()
                if mname in txt:
                    for m in re.finditer(p,txt):
                        cnt+=1
                        lineno = txt.count("\n",0,m.start()+1)+1
                        res = (m.groups()[2].strip(),lineno)
                        if fn not in inst_dict:
                            inst_dict[fn] = [res]
                        else:
                            inst_dict[fn].append(res)
        if inst_dict:
            v = sublime.active_window().new_file()
            v.set_name(mname + ' Instances')
            v.set_syntax_file('Packages/SystemVerilog/Find Results SV.hidden-tmLanguage')
            v.settings().set("result_file_regex", r"^(.+):$")
            v.settings().set("result_line_regex", r"\(line: (\d+)\)$")
            v.set_scratch(True)
            txt = mname + ': %0d instances.\n\n' %(cnt)
            for (name,il) in inst_dict.items():
                txt += name + ':\n'
                for i in il:
                    txt += '    - {0} (line: {1})\n'.format(i[0].strip(),i[1])
                txt += '\n'
            v.run_command('insert_snippet',{'contents':str(txt)})
        else :
            sublime.status_message("No instance found !")

####################################################################
# Analyze code and do various check: unused/undeclared signals ... #
class VerilogLintingCommand(sublime_plugin.TextCommand):

    def run(self,edit, unused="False", undeclared="False"):
        self.txt = self.view.substr(sublime.Region(0,self.view.size()))
        self.txt = verilogutil.clean_comment(self.txt)
        self.mi = verilogutil.parse_module(self.txt,r'\w+')
        self.result = {"unused":"", "undeclared":""}
        self.unused = None
        if self.mi:
            if undeclared=="True":
                self.find_undeclared()
            if unused=="True":
                self.find_unused()
        # Print result
        if self.unused:
            re_str = '(?<!\.)(' + '|'.join(r'\b{0}\b'.format(s) for s in self.unused) + ')'
            rl = self.view.find_all(re_str)
            self.view.sel().clear()
            self.view.sel().add_all(rl)
            panel = sublime.active_window().show_input_panel("Unused signal to remove", self.result["unused"], self.on_prompt_done, None, None)
        else:
            self.print_result()


    def find_undeclared(self):
        signals = []
        re_sig = re.compile(r'(?s)(?<!(?:\.|:|\'|\$))\b([A-Za-z_]\w+)\b(?!:)',re.MULTILINE)
        # Collect all words part of an assign
        tmp = re.findall(r'(?s)^\s*(?:assign\s+)?(\w+\b\s*<?=.*?);',self.txt,re.MULTILINE)
        for x in tmp:
            signals += re_sig.findall(x)
        # Collect all words part of sensibility list
        tmp = re.findall(r'(?s)@\s*\((.*?)\)',self.txt,re.MULTILINE)
        for x in tmp:
            x = re.sub(r'\b(pos|neg)?edge\b','',x)
            signals += re_sig.findall(x)
        # Collect all words part of binding (does not work with implicit binding ...)
        tmp = re.findall(r'(?s)\.[A-Za-z_]\w+\s*\((.*?)\)',self.txt,re.MULTILINE)
        for x in tmp:
            signals += re_sig.findall(x)
        # Extract the list of declared signals/port/param
        decl = []
        for x in self.mi['signal']:
            if x['tag']=='enum' :
                decl += verilogutil.get_enum_values(x['decl'])
            else :
                decl.append(x['name'])
        for x in self.mi['port']:
            decl.append(x['name'])
        for x in self.mi['param']:
            decl.append(x['name'])
        for x in self.mi['inst']:
            decl.append(x['name'])
        # Remove duplicate and check that each signals is inside the list of declared signals
        signals = list(set(signals)) # remove duplicate
        signals = [s for s in signals if s not in ['and','or','int']] # remove false positive
        undecl = [s for s in signals if s not in decl]
        if undecl:
            # Check for enum
            # Look for import package to be sure signals/constant used were not declared in a package
            imps = re.findall(r'(?s)^\s*import\s*(.*?);',self.txt,re.MULTILINE)
            if imps:
                pkgs = []
                decl = []
                for imp in imps:
                    pkgs += re.findall(r'\b(\w+)::',imp)
                for pkg in pkgs:
                    pi = verilog_module.lookup_package(self.view,pkg)
                    if pi:
                        decl += [x['name'] for x in pi['member'] if x['tag'] in ['decl']]
                        for x in pi['member'] :
                            if x['tag']=='enum':
                                decl += verilogutil.get_enum_values(x['decl'])
                undecl = [x for x in undecl if x not in decl]
            if undecl:
                self.result["undeclared"] = ', '.join([x for x in undecl])

    def find_unused(self):
        sl = [x['name'] for x in self.mi['signal']]
        words = re.findall(r'(?<!\.)\w+',self.txt,re.MULTILINE)
        cnt = Counter(words)
        self.unused = [s for s in sl if cnt[s]==1]
        self.result["unused"] = ', '.join(self.unused)
        self.sid = {x['name']:x for x in self.mi['signal'] if x['name'] in self.result["unused"]}

    # Remove all signals kept in the input panel
    def on_prompt_done(self, content):
        if content.strip():
            self.view.run_command("verilog_delete_signal", {"args":{'signals':content, 'sid':self.sid}})
        self.print_result()

    # Display in a panel all linting result
    def print_result(self):
        s = ''
        if self.result["undeclared"]:
            s+='Found undeclared signals: {0}\n'.format(self.result["undeclared"])
        if self.result["unused"]:
            s+='Found unused signals: {0}\n'.format(self.result["unused"])
        if s:
            sublimeutil.print_to_panel(s,'SystemVerilog')
        else:
            sublime.status_message('Linting successful: no issue found')


# Command to delete a list of signal declaration
class VerilogDeleteSignalCommand(sublime_plugin.TextCommand):

    def run(self,edit, args):
        sl = args['signals'].split(', ')
        cnt = 0
        for s in sl:
            re_str = r'^\s*' + args['sid'][s]['decl']+r'\s*;'
            re_str = re.sub(r'\s+','\s+',re_str)
            re_str = re.sub(r'\[','\[',re_str)
            re_str = re.sub(r'\]','\]',re_str)
            re_str = re.sub(r'\(','\(',re_str)
            re_str = re.sub(r'\)','\)',re_str)
            r = self.view.find(re_str,0)
            if not r.empty():
                self.view.erase(edit,r)
                cnt +=1
                self.delete_comment_line(edit,r)
            # Could not find it ? certainly inside a list:
            else :
                re_str = r'(,\s*)?\b' + s + r'\b(\s*,)?'
                m_str = ''
                r_tmp_a = self.view.find_all(re_str,0)
                for r in r_tmp_a :
                    t = self.view.substr(r)
                    if t.startswith(','):
                        if t.endswith(','):
                            r.b -=1
                        self.view.erase(edit,r)
                        cnt +=1
                        self.delete_comment_line(edit,r)
                    elif t.endswith(','):
                        self.view.erase(edit,r)
                        cnt +=1
                        self.delete_comment_line(edit,r)
        sublime.status_message('Removed %d declaration(s)' % (cnt))
        # cleanup empty declaration
        if cnt>0:
            rl = [r for r in self.view.sel() if not r.empty()]
            self.view.sel().clear()
            self.view.sel().add_all(rl)

    def delete_comment_line(self,edit,r):
        r_tmp = self.view.full_line(r.a)
        m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
        if m:
            self.view.erase(edit,r_tmp)
