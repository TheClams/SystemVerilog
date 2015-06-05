import sublime, sublime_plugin
import re, string, os, sys, functools, mmap, pprint, imp
from collections import Counter
from plistlib import readPlistFromBytes

try:
    from SystemVerilog import verilog_module
    import verilog_module
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    import verilog_module

try:
    from SystemVerilog.verilogutil import verilogutil
    from SystemVerilog.verilogutil import sublimeutil
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
    import verilogutil
    import sublimeutil


############################################################################
# Init
TOOLTIP_SUPPORT = int(sublime.version()) >= 3072

use_tooltip = False
sv_settings = None
tooltip_css = ''

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(sublimeutil)
    imp.reload(verilog_module)
    global sv_settings
    global pref_settings
    pref_settings = sublime.load_settings('Preferences.sublime-settings')
    pref_settings.clear_on_change('reload')
    pref_settings.add_on_change('reload',plugin_loaded)
    sv_settings = sublime.load_settings('SystemVerilog.sublime-settings')
    sv_settings.clear_on_change('reload')
    sv_settings.add_on_change('reload',plugin_loaded)
    init_css()

def init_css():
    global use_tooltip
    global tooltip_css
    if int(sublime.version()) >= 3072 :
        use_tooltip = sv_settings.get('sv.tooltip',True)
        color_plist = readPlistFromBytes(sublime.load_binary_resource(pref_settings.get('color_scheme')))
        color_dict = {x['scope']:x['settings'] for x in color_plist['settings'] if 'scope' in x}
        color_dict['__GLOBAL__'] = color_plist['settings'][0]['settings'] # first settings contains global settings, without scope(hopefully)
        #pprint.pprint(color_dict, width=200)
        bg = int(color_dict['__GLOBAL__']['background'][1:],16)
        fg = int(color_dict['__GLOBAL__']['foreground'][1:],16)
        # Get color for keyword, support, storage, default to foreground
        kw  = fg if 'keyword' not in color_dict else int(color_dict['keyword']['foreground'][1:],16)
        sup = fg if 'support' not in color_dict else int(color_dict['support']['foreground'][1:],16)
        sto = fg if 'storage' not in color_dict else int(color_dict['storage']['foreground'][1:],16)
        ent = fg if 'entity' not in color_dict else int(color_dict['entity']['foreground'][1:],16)
        fct = fg if 'support.function' not in color_dict else int(color_dict['support.function']['foreground'][1:],16)
        op  = fg if 'keyword.operator' not in color_dict else int(color_dict['keyword.operator']['foreground'][1:],16)
        num = fg if 'constant.numeric' not in color_dict else int(color_dict['constant.numeric']['foreground'][1:],16)
        st  = fg if 'string' not in color_dict else int(color_dict['string']['foreground'][1:],16)
        # Create background and border color based on the background color
        b = bg & 255
        g = (bg>>8) & 255
        r = (bg>>16) & 255
        if b > 128:
            bgHtml = b - 0x33
            bgBody = b - 0x20
        else:
            bgHtml = b + 0x33
            bgBody = b + 0x20
        if g > 128:
            bgHtml += (g - 0x33)<<8
            bgBody += (g - 0x20)<<8
        else:
            bgHtml += (g + 0x33)<<8
            bgBody += (g + 0x20)<<8
        if r > 128:
            bgHtml += (r - 0x33)<<16
            bgBody += (r - 0x20)<<16
        else:
            bgHtml += (r + 0x33)<<16
            bgBody += (r + 0x20)<<16
        tooltip_css = 'html {{ background-color: #{bg:06x}; color: #{fg:06x}; }}\n'.format(bg=bgHtml, fg=fg)
        tooltip_css+= 'body {{ background-color: #{bg:06x}; margin: 1px; font-size: 1em; }}\n'.format(bg=bgBody)
        tooltip_css+= 'p {padding-left: 0.6em;}\n'
        tooltip_css+= '.content {margin: 0.8em;}\n'
        tooltip_css+= '.keyword {{color: #{c:06x};}}\n'.format(c=kw)
        tooltip_css+= '.support {{color: #{c:06x};}}\n'.format(c=sup)
        tooltip_css+= '.storage {{color: #{c:06x};}}\n'.format(c=sto)
        tooltip_css+= '.function {{color: #{c:06x};}}\n'.format(c=fct)
        tooltip_css+= '.entity {{color: #{c:06x};}}\n'.format(c=ent)
        tooltip_css+= '.operator {{color: #{c:06x};}}\n'.format(c=op)
        tooltip_css+= '.numeric {{color: #{c:06x};}}\n'.format(c=num)
        tooltip_css+= '.string {{color: #{c:06x};}}\n'.format(c=st)
        tooltip_css+= '.extra-info {font-size: 0.9em; }\n'
        #print(tooltip_css)
    else :
       use_tooltip  = False
       tooltip_css = ''

############################################################################
# Display type of the signal/variable under the cursor into the status bar #
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
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
        # TODO: handle multiple level
        if region.a>1 and self.view.substr(sublime.Region(region.a-1,region.a))=='.' :
            if 'support.function.port' not in self.view.scope_name(region.a):
                region.a = self.view.find_by_class(region.a-3,False,sublime.CLASS_WORD_START)
        # Optionnaly extend selection to scope specifier
        if region.a>2 and self.view.substr(sublime.Region(region.a-2,region.a))=='::' :
            region.a = self.view.find_by_class(region.a-3,False,sublime.CLASS_WORD_START)
        v = self.view.substr(region)
        # print(v)
        if re.match(r'^([A-Za-z_]\w*::|([A-Za-z_]\w*\.)+)?[A-Za-z_]\w*$',v): # Check this is valid a valid word
            s,ti = self.get_type(v,region)
            if not s:
                sublime.status_message('No definition found for ' + v)
            # Check if we use tooltip or statusbar to display information
            elif use_tooltip :
                if ti and (ti['type'] in ['module','interface','function','task']):
                    s,_ = self.color_str(s=s, addLink=True,ti_var=ti)
                    if 'param' in ti:
                        for p in ti['param'] :
                            d = 'parameter {t} {n} = {v}'.format(t=p['decl'],n=p['name'],v=p['value'])
                            s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(d)[0])
                    if 'port' in ti:
                        for p in ti['port'] :
                            s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(p['decl'])[0])
                elif ti and 'tag' in ti and (ti['tag'] == 'enum' or ti['tag']=='struct'):
                    m = re.search(r'(?s)^(.*)\{(.*)\}', ti['decl'])
                    # print(ti)
                    s,tti = self.color_str(s=m.groups()[0] + ' ' + v, addLink=True)
                    if ti['tag'] == 'enum':
                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[1])
                    else :
                        fti = verilogutil.get_all_type_info(m.groups()[1])
                        if fti:
                            for ti in fti:
                                s += '<br>{0}{1}'.format('&nbsp;'*4,self.color_str(ti['decl'])[0])
                elif ti and ti['type']=='class':
                    ci = verilogutil.parse_class_file(ti['fname'][0],ti['name'])
                    s,_ = self.color_str(s='class {0}'.format(ti['name']), addLink=True,ti_var=ti)
                    if ci['extend']:
                        s+=' <span class="keyword">extends</span> '
                        s+='<span class="storage">{0}</span>'.format(ci['extend'])
                    for x in ci['member']:
                        if 'access' not in x:
                            s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(x['decl'])[0])
                    for x in ci['function']:
                        if 'access' not in x and x['name']!='new':
                            s+='<br><span class="extra-info">{0}<span class="keyword">function </span><span class="function">{1}</span>()</span>'.format('&nbsp;'*4,x['name'])
                    # print(ci)
                else :
                    s,ti = self.color_str(s=s, addLink=True)
                    if ti:
                        if 'tag' in ti and ti['tag'] == 'enum':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[0])
                        elif 'tag' in ti and ti['tag'] == 'struct':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                fti = verilogutil.get_all_type_info(m.groups()[0])
                                if fti:
                                    for ti in fti:
                                        s += '<br>{0}{1}'.format('&nbsp;'*4,self.color_str(ti['decl'])[0])
                        elif 'interface' in ti['decl']:
                            mi = verilog_module.lookup_module(self.view,ti['name'])
                            if mi :
                                # pprint.pprint(mi)
                                #TODO: use modport info if it exists
                                if 'param' in mi:
                                    for p in mi['param'] :
                                        d = 'parameter {t} {n} = {v}'.format(t=p['decl'],n=p['name'],v=p['value'])
                                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(d)[0])
                                for x in mi['signal']:
                                    if x['tag']=='decl':
                                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(x['decl'])[0])
                                if 'modport' in mi:
                                    for p in mi['modport'] :
                                        d = 'modport {n}'.format(n=p['name'])
                                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(d)[0])
                        elif ti['type']=='class':
                            ci = verilogutil.parse_class_file(ti['fname'][0],ti['name'])
                            if ci:
                                for x in ci['member']:
                                    if 'access' not in x:
                                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,self.color_str(x['decl'])[0])
                                for x in ci['function']:
                                    if 'access' not in x and x['name']!='new':
                                        s+='<br><span class="extra-info">{0}<span class="keyword">function </span><span class="function">{1}</span>()</span>'.format('&nbsp;'*4,x['name'])
                s = '<style>{css}</style><div class="content">{txt}</div>'.format(css=tooltip_css, txt=s)
                self.view.show_popup(s,location=-1, max_width=500, on_navigate=self.on_navigate)
            else :
                # fix hard limit to signal declaration to 128 to ensure it can be displayed
                if s and len(s) > 128:
                    s = re.sub(r'\{.*\}','',s) # A long signal is typical of an enum, struct : remove content to only let the type appear
                    if len(s) > 128:
                        s = s[:127]
                sublime.status_message(s)

    def get_type(self,var_name,region):
        scope = self.view.scope_name(region.a)
        ti = None
        txt = ''
        # In case of field, retrieve parent type
        if '.' in var_name:
            s = var_name.split('.')
            if len(s)>1 :
                lines = self.view.substr(sublime.Region(0, self.view.line(region).b))
                ti = verilogutil.get_type_info(lines,s[0])
                #TODO: handle multiple level
                # Get type definition
                if ti['type']:
                    if ti['type']=='module':
                        ti = verilog_module.lookup_module(self.view,ti['name'])
                    else:
                        ti = verilog_module.lookup_type(self.view,ti['type'])
                    # Lookup for the variable inside the type defined
                    if ti:
                        fname = ti['fname'][0]
                        ti = verilogutil.get_type_info_file(fname,s[1])
                        if ti['type'] in ['function', 'task']:
                            with open(fname) as f:
                                flines = verilogutil.clean_comment(f.read())
                            ti = verilogutil.parse_function(flines,s[1])
                        txt = ti['decl']
        # Extract type info from module if we are on port connection
        elif 'support.function.port' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.inst',region)
            txt = self.view.substr(region)
            mname = re.search(r'\w+',txt).group(0)
            #print('[get_type] Find module with name {0}'.format(mname))
            mi = verilog_module.lookup_module(self.view,mname)
            if mi:
                for p in mi['port']:
                    if p['name']==var_name:
                        txt = p['decl']
                        break
        # Get function I/O
        elif 'support.function.generic' in scope:
            ti = verilog_module.lookup_function(self.view,var_name)
            # print ('[get_type] Function: {0}'.format(ti))
            if ti:
                txt = ti['decl']
        # Get structure/interface
        elif 'storage.type.userdefined' in scope or 'storage.type.uvm' in scope:
            ti = verilog_module.lookup_type(self.view,var_name)
            txt = ti['decl']
        # Get Module I/O
        elif 'storage.module' in scope:
            ti = verilog_module.lookup_module(self.view,var_name)
            if ti:
                txt = ti['type'] + ' ' + var_name
        # Get Macro text
        elif 'constant.other.define' in scope:
            filelist = self.view.window().lookup_symbol_in_index(var_name)
            if filelist:
                for fi in filelist:
                    fname = sublimeutil.normalize_fname(fi[0])
                    with open(fname,'r') as f:
                        flines = str(f.read())
                    txt = verilogutil.get_macro(flines,var_name)
                    if txt:
                        break
        # Variable inside a scope
        elif '::' in var_name:
            vs = var_name.split('::')
            if len(vs)==2:
                ti = verilog_module.lookup_type(self.view,vs[0])
                if ti and ti['type']=='package':
                    ti = verilogutil.get_type_info_file(ti['fname'][0],vs[1])
                    if ti:
                        txt = ti['decl']
        # Simply lookup in the file before the use of the variable
        else :
            # select whole file until end of current line
            region = self.view.line(region)
            lines = self.view.substr(sublime.Region(0, region.b))
            # Extract type
            ti = verilogutil.get_type_info(lines,var_name)
            # Type not found in current file ? fallback to sublime index
            if not ti['decl']:
                ti = verilog_module.lookup_type(self.view,var_name)
            if ti:
                txt = ti['decl']
                if 'value' in ti and ti['value']:
                    txt += ' = ' + ti['value']
        return txt,ti

    keywords = ['localparam', 'parameter', 'module', 'interface', 'package', 'class', 'typedef', 'struct', 'union', 'enum', 'packed', 'automatic',
                'local', 'protected', 'public', 'static', 'const', 'virtual', 'function', 'task', 'var', 'modport', 'clocking', 'extends']

    def color_str(self,s, addLink=False, ti_var=None):
        ss = s.split()
        sh = ''
        ti = None
        pos_var = len(ss)-1
        if pos_var>2 and ss[-2] == '=':
            pos_var -= 2
        for i,w in enumerate(ss):
            m = re.match(r'^[A-Za-z_]\w?',w)
            if '"' in w :
                sh+=re.sub(r'(".*?")',r'<span class="string">\1</span> ',w)
            elif i == len(ss)-1:
                if m:
                    if addLink and ti_var and 'fname' in ti_var:
                        fname = '{0}:{1}:{2}'.format(ti_var['fname'][0],ti_var['fname'][1],ti_var['fname'][2])
                        w ='<a href="{1}@{0}" class="entity">{1}</a>'.format(fname,w)
                else:
                    w = re.sub(r'\b((b|d|o)?\d+(\.\d+(ms|us|ns|ps|fs)?)?)\b',r'<span class="numeric">\1</span>',w)
                    w = re.sub(r'(\'h[0-9A-Fa-f]+)\b',r'<span class="numeric">\1</span>',w)
                    w = re.sub(r'(\#|\:|\')',r'<span class="operator">\1</span>',w)
                sh+=w
            elif w in ['input', 'output', 'inout']:
                sh+='<span class="support">{0}</span> '.format(w)
            elif w in self.keywords:
                sh+='<span class="keyword">{0}</span> '.format(w)
            elif w in ['wire', 'reg', 'logic', 'int', 'signed', 'unsigned', 'real', 'bit', 'rand', 'void', 'string']:
                sh+='<span class="storage">{0}</span> '.format(w)
            elif '::' in w:
                ws = w.split('::')
                sh+='<span class="support">{0}</span><span class="operator">::</span>'.format(ws[0])
                if addLink:
                    ti = verilog_module.lookup_type(self.view,ws[1])
                if ti and 'fname' in ti:
                    fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                    sh+='<a href="{1}@{0}" class="storage">{1}</a> '.format(fname,ws[1])
                else:
                    sh+='<span class="storage">{0}</span> '.format(ws[1])
            elif '.' in w:
                ws = w.split('.')
                if addLink:
                    ti = verilog_module.lookup_type(self.view,ws[0])
                if ti and 'fname' in ti:
                    fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                    sh+='<a href="{1}@{0}" class="storage">{1}</a>'.format(fname,ws[0])
                else:
                    sh+='<span class="storage">{0}</span>'.format(ws[0])
                sh+='.<span class="support">{0}</span> '.format(ws[1])
            elif '[' in w or '(' in w:
                w = re.sub(r'\b(\d+)\b',r'<span class="numeric">\1</span>',w)
                sh += re.sub(r'(\#|\:)',r'<span class="operator">\1</span>',w) + ' '
            # Color type: typically just before the variable or one word earlier in case of array or parameter
            elif (i == pos_var-1 and m) or (i == pos_var-2 and ('[' in ss[pos_var-1] or '#' in ss[pos_var-1])) :
                if addLink:
                    ti = verilog_module.lookup_type(self.view,w)
                # print('word={0} => ti={1}'.format(w,ti))
                if ti and 'fname' in ti:
                    fname = '{0}:{1}:{2}'.format(ti['fname'][0],ti['fname'][1],ti['fname'][2])
                    sh+='<a href="{1}@{0}" class="storage">{1}</a> '.format(fname,w)
                else:
                    sh+='<span class="storage">{0}</span> '.format(w)
            elif re.match(r'\d+',w) :
                sh += re.sub(r'\b(\d+)\b',r'<span class="numeric">\1</span> ',w)
            elif w in ['='] :
                sh += re.sub(r'(\=)',r'<span class="operator">\1</span> ',w)
            else:
                sh += w + ' '
        return sh,ti

    def on_navigate(self, href):
        href_s = href.split('@')
        pos = sublime.Region(0,0)
        v = self.view.window().open_file(href_s[1], sublime.ENCODED_POSITION)

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
        v = self.view.substr(region).strip()
        v_word = r'\b'+v+r'\b'
        # look for an input or an interface of the current module, and for an assignement
        sl = [r'input\s+(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:]*\s+)?(\[[\w\:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?' + v + r'\b']
        sl.append(r'^\s*\w+\.\w+\s+' + v + r'\b')
        sl.append(r'\b' + v + r'\b\s*<?\=[^\=]')
        for s in sl:
            r = self.view.find(s,0)
            # print('searching ' + s + ' => ' + str(r))
            if r:
                # print("Found input at " + str(r) + ': ' + self.view.substr(self.view.line(r)))
                sublimeutil.move_cursor(self.view,r.a)
                return
        # look for a connection explicit, implicit or by position
        sl = [r'\.(\w+)\s*\(\s*'+v+r'\b' , r'(\.\*)', r'(\(|,)\s*'+v+r'\b\s*(,|\)\s*;)']
        for k,s in enumerate(sl):
            pl = []
            rl = self.view.find_all(s,0,r'$1',pl)
            # print('searching ' + s + ' => ' + str(rl))
            for i,r in enumerate(rl):
                # print('Found in line ' + self.view.substr(self.view.line(r)))
                # print('Scope for ' + str(r) + ' = ' + self.view.scope_name(r.a))
                if 'meta.module.inst' in self.view.scope_name(r.a) :
                    rm = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
                    txt = verilogutil.clean_comment(self.view.substr(rm))
                    # Parse module definition
                    mname = re.findall(r'\w+',txt)[0]
                    filelist = self.view.window().lookup_symbol_in_index(mname)
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
                            portname = v
                        elif k==0: #implicit connection
                            portname = pl[i]
                        elif k==2 : #connection by position
                            for j,l in enumerate(txt.split(',')) :
                                if v in l:
                                    dl = [x['decl'] for x in mi['port']]
                                    if re.search(op,dl[j]) :
                                        r_v = self.view.find(v_word,rm.a)
                                        if r_v and r_v.b<=rm.b:
                                            sublimeutil.move_cursor(self.view,r_v.a)
                                        else:
                                            sublimeutil.move_cursor(self.view,r.a)
                                        return
                        if portname != '' :
                            op += portname+r'\b'
                            for x in mi['port']:
                                m = re.search(op,x['decl'])
                                if m:
                                    r_v = self.view.find(v_word,rm.a)
                                    if r_v and r_v.b<=rm.b:
                                        sublimeutil.move_cursor(self.view,r_v.a)
                                    else:
                                        sublimeutil.move_cursor(self.view,r.a)
                                    return
        # Everything failed
        sublime.status_message("Could not find driver of " + v)


############################################################################
# Helper function to retrieve current module name based on cursor position #

def getModuleName(view):
    r = view.sel()[0]
    # Empty selection ? get current module name
    if r.empty():
        p = r'(?s)^[ \t]*(module|interface)\s+(\w+\b)'
        mnameList = []
        rList = view.find_all(p,0,r'\2',mnameList)
        mname = ''
        # print(rList)
        # print(mnameList)
        if rList:
            # print(nl)
            for (rf,n) in zip(rList,mnameList):
                if rf.a < r.a:
                    mname = n
                else:
                    break
    else:
        mname = view.substr(r)
    # print(mname)
    return mname

######################################################################################
# Create a new buffer showing the hierarchy (sub-module instances) of current module #
class VerilogShowHierarchyCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        mname = getModuleName(self.view)
        txt = self.view.substr(sublime.Region(0, self.view.size()))
        txt = verilogutil.clean_comment(txt)
        mi = verilogutil.parse_module(txt,mname)
        if not mi:
            print('[VerilogShowHierarchyCommand] Not inside a module !')
            return
        sublime.status_message("Show Hierarchy can take some time, please wait ...")
        sublime.set_timeout_async(lambda mi=mi, w=self.view.window(), txt=txt: self.showHierarchy(mi,w,txt))

    def showHierarchy(self,mi,w,txt):
        # Create Dictionnary where each type is associated with a list of tuple (instance type, instance name)
        self.d = {}
        top_level = mi['name']
        self.d[mi['name']] = [(x['type'],x['name']) for x in mi['inst']]
        li = [x['type'] for x in mi['inst']]
        while li :
            # print('Loop on list with {1} elements : {2}'.format(len(li),li))
            li_next = []
            for i in li:
                if i not in self.d.keys():
                    filelist = w.lookup_symbol_in_index(i)
                    if filelist:
                        for f in filelist:
                            fname = sublimeutil.normalize_fname(f[0])
                            mi = verilogutil.parse_module_file(fname,i)
                            if mi:
                                break
                    # Not in project ? try in current file
                    else :
                        mi = verilogutil.parse_module(txt,i)
                    if mi:
                        li_next += [x['type'] for x in mi['inst']]
                        self.d[i] = [(x['type'],x['name']) for x in mi['inst']]
            li = list(set(li_next))
        txt = top_level + '\n'
        txt += self.printSubmodule(top_level,1)

        v = sublime.active_window().new_file()
        v.set_name(top_level + ' Hierarchy')
        v.set_syntax_file('Packages/SystemVerilog/Find Results SV.hidden-tmLanguage')
        v.set_scratch(True)
        v.run_command('insert_snippet',{'contents':str(txt)})

    def printSubmodule(self,name,lvl):
        txt = ''
        if name in self.d:
            # print('printSubmodule ' + str(self.d[name]))
            for x in self.d[name]:
                txt += '    '*lvl+'+ '+x[1]+'    ('+x[0]+')\n'
                # txt += '    '*lvl+'+ '+x[0]+' '+x[1]+'\n'
                txt += self.printSubmodule(x[0],lvl+1)
        return txt

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
            verilog_module.VerilogModuleInstCommand.get_list_file(None,projname,None)
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

#############################################
# Find all unused signals in current module #
class VerilogFindUnusedCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        txt = self.view.substr(sublime.Region(0,self.view.size()))
        txt = verilogutil.clean_comment(txt)
        mi = verilogutil.parse_module(txt,r'\w+')
        if not mi:
            sublime.status_message('No module found !')
            return
        sl = [x['name'] for x in mi['signal']]
        self.us = ''
        words = re.findall(r'(?<!\.)\w+',txt,re.MULTILINE)
        cnt = Counter(words)
        for s in sl:
            if cnt[s]==1 :
                if self.us:
                    self.us += ', '
                self.us += s
        self.sid = {x['name']:x for x in mi['signal'] if x['name'] in self.us}
        if self.us:
            sl = self.us.split(', ')
            re_str = '(?<!\.)('
            for i,s in enumerate(sl):
                re_str += r'\b'+s+r'\b'
                if i!=len(sl)-1:
                    re_str+='|'
            re_str += ')'
            rl = self.view.find_all(re_str)
            self.view.sel().clear()
            self.view.sel().add_all(rl)
            panel = sublime.active_window().show_input_panel("Unused signal to remove", self.us, self.on_prompt_done, None, None)
        else:
            sublime.status_message('No unused signals !')

    # Remove all signals kept in the input panel
    def on_prompt_done(self, content):
        self.view.run_command("verilog_delete_signal", {"args":{'signals':content, 'sid':self.sid}})


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
