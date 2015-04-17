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

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(sublimeutil)
    imp.reload(verilog_module)


############################################################################
# Init
TOOLTIP_SUPPORT = int(sublime.version()) >= 3072

use_tooltip = False
sv_settings = None
tooltip_css = ''

def plugin_loaded():
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
        op = fg if 'keyword.operator' not in color_dict else int(color_dict['keyword.operator']['foreground'][1:],16)
        num = fg if 'constant.numeric' not in color_dict else int(color_dict['constant.numeric']['foreground'][1:],16)
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
        tooltip_css+= '.operator {{color: #{c:06x};}}\n'.format(c=op)
        tooltip_css+= '.numeric {{color: #{c:06x};}}\n'.format(c=num)
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
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region)
        if re.match(r'^\w+$',v): # Check this is valid a valid word
            s,ti = self.get_type(v,region)
            if not s:
                sublime.status_message('No definition found for ' + v)
            # Check if we use tooltip or statusbar to display information
            elif use_tooltip :
                if ti and (ti['tag'] == 'enum' or ti['tag']=='struct'):
                    m = re.search(r'(?s)^(.*)\{(.*)\}', ti['decl'])
                    print(ti)
                    s,tti = self.color_str(s=m.groups()[0] + ' ' + v, addLink=True)
                    if ti['tag'] == 'enum':
                        s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[1])
                    else :
                        fti = verilogutil.get_all_type_info(m.groups()[1])
                        if fti:
                            for ti in fti:
                                s += '<br>{0}{1}'.format('&nbsp;'*4,self.color_str(ti['decl'])[0])
                else :
                    s,ti = self.color_str(s=s, addLink=True)
                    if ti:
                        # print(ti)
                        if ti['tag'] == 'enum':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                s+='<br><span class="extra-info">{0}{1}</span>'.format('&nbsp;'*4,m.groups()[0])
                        elif ti['tag'] == 'struct':
                            m = re.search(r'\{(.*)\}', ti['decl'])
                            if m:
                                fti = verilogutil.get_all_type_info(m.groups()[0])
                                if fti:
                                    for ti in fti:
                                        s += '<br>{0}{1}'.format('&nbsp;'*4,self.color_str(ti['decl'])[0])
                        elif 'interface' in ti['decl']:
                            mi = verilog_module.lookup_module(self.view,ti['name'])
                            if mi :
                                #TODO: use modport info if it exists
                                for x in mi['signal']:
                                    if x['tag']=='decl':
                                        s+='<br>{0}{1}'.format('&nbsp;'*4,self.color_str(x['decl'])[0])
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
        # Extract type info from module if we are on port connection
        if 'support.function.port' in scope:
            region = sublimeutil.expand_to_scope(self.view,'meta.module.inst',region)
            txt = self.view.substr(region)
            mname = re.search(r'\w+',txt).group(0)
            #print('Find module with name {0}'.format(mname))
            mi = verilog_module.lookup_module(self.view,mname)
            if mi:
                for p in mi['port']:
                    if p['name']==var_name:
                        txt = p['decl']
                        break
        elif 'storage.type.userdefined' in scope:
            ti = verilog_module.lookup_type(self.view,var_name)
            txt = ti['decl']
        # Simply lookup in the file before the use of the variable
        else :
            # select whole file until end of current line
            region = self.view.line(region)
            txt = self.view.substr(sublime.Region(0, region.b))
            # Extract type
            ti = verilogutil.get_type_info(txt,var_name)
            # print (ti)
            txt = ti['decl']
        return txt,ti

    keywords = ['localparam', 'parameter', 'module', 'interface', 'package', 'typedef', 'struct', 'union', 'enum', 'packed',
                'local', 'protected', 'public', 'static', 'const', 'virtual', 'function', 'var']

    def color_str(self,s, addLink=False):
        ss = s.split(' ')
        sh = ''
        ti = None
        for i,w in enumerate(ss):
            m = re.match(r'^\w+',w)
            if i == len(ss)-1:
                if '[' in w :
                    w = re.sub(r'\b(\d+)\b',r'<span class="numeric">\1</span>',w)
                    sh += re.sub(r'(\#|\:)',r'<span class="operator">\1</span>',w)
                else:
                    sh+=w
            elif w in ['input', 'output', 'inout']:
                sh+='<span class="support">{0}</span> '.format(w)
            elif w in self.keywords:
                sh+='<span class="keyword">{0}</span> '.format(w)
            elif w in ['wire', 'reg', 'logic', 'int', 'signed', 'unsigned', 'real', 'bit', 'rand']:
                sh+='<span class="storage">{0}</span> '.format(w)
            elif '::' in w:
                ws = w.split('::')
                sh+='<span class="support">{0}</span><span class="operator">::</span>'.format(ws[0])
                if addLink:
                    ti = verilog_module.lookup_type(self.view,ws[1])
                if ti and 'fname' in ti:
                    sh+='<a href="{1}@{0}" class="storage">{1}</a> '.format(ti['fname'],ws[1])
                else:
                    sh+='<span class="storage">{0}</span> '.format(ws[1])
            elif '.' in w:
                ws = w.split('.')
                if addLink:
                    ti = verilog_module.lookup_type(self.view,ws[0])
                if ti and 'fname' in ti:
                    sh+='<a href="{1}@{0}" class="storage">{1}</a>'.format(ti['fname'],ws[0])
                else:
                    sh+='<span class="storage">{0}</span>'.format(ws[0])
                sh+='.<span class="support">{0}</span> '.format(ws[1])
            elif '[' in w or '(' in w:
                w = re.sub(r'\b(\d+)\b',r'<span class="numeric">\1</span>',w)
                sh += re.sub(r'(\#|\:)',r'<span class="operator">\1</span>',w) + ' '
            elif (i == len(ss)-2 and m) or (i == len(ss)-3 and '[' in ss[-2]):
                if addLink:
                    ti = verilog_module.lookup_type(self.view,w)
                if ti and 'fname' in ti:
                    sh+='<a href="{1}@{0}" class="storage">{1}</a> '.format(ti['fname'],w)
                else:
                    sh+='<span class="storage">{0}</span> '.format(w)
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


######################################################################################
# Create a new buffer showing the hierarchy (sub-module instances) of current module #
class VerilogShowHierarchyCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        txt = self.view.substr(sublime.Region(0, self.view.size()))
        txt = verilogutil.clean_comment(txt)
        mi = verilogutil.parse_module(txt,r'\b\w+\b')
        if not mi:
            print('[VerilogShowHierarchyCommand] Not inside a module !')
            return
        # Create Dictionnary where each type is associated with a list of tuple (instance type, instance name)
        self.d = {}
        top_level = mi['name']
        self.d[mi['name']] = [(x['type'],x['name']) for x in mi['inst']]
        li = [x['type'] for x in mi['inst']]
        while li:
            # print('Looping on list ' + str(li))
            li_next = []
            for i in li:
                if i not in self.d.keys():
                    filelist = self.view.window().lookup_symbol_in_index(i)
                    if filelist:
                        for f in filelist:
                            fname = sublimeutil.normalize_fname(f[0])
                            mi = verilogutil.parse_module_file(fname,i)
                            if mi:
                                break
                        if mi:
                            li_next += [x['type'] for x in mi['inst']]
                            self.d[i] = [(x['type'],x['name']) for x in mi['inst']]
            li = li_next
        txt = top_level + '\n'
        txt += self.print_submodule(top_level,1)

        v = sublime.active_window().new_file()
        v.set_name(top_level + ' Hierarchy')
        v.set_syntax_file('Packages/SystemVerilog/Find Results SV.hidden-tmLanguage')
        v.set_scratch(True)
        v.run_command('insert_snippet',{'contents':str(txt)})

    def print_submodule(self,name,lvl):
        txt = ''
        if name in self.d:
            # print('print_submodule ' + str(self.d[name]))
            for x in self.d[name]:
                txt += '    '*lvl+'+ '+x[1]+'    ('+x[0]+')\n'
                # txt += '    '*lvl+'+ '+x[0]+' '+x[1]+'\n'
                txt += self.print_submodule(x[0],lvl+1)
        return txt

###########################################################
# Find all instances of current module or selected module #
class VerilogFindInstanceCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        # Empty selection ? get current module name. might get funky in multi-module file ...
        if self.view.sel()[0].empty():
            txt = self.view.substr(sublime.Region(0, self.view.size()))
            txt = verilogutil.clean_comment(txt)
            m = re.search(r"(?s)^\s*(?P<type>module|interface)\s+(?P<name>\w+\b)",txt, re.MULTILINE)
            if not m:
                return
            mname = m.group('name')
        else:
            mname = self.view.substr(self.view.sel()[0])
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
