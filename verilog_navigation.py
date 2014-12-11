import sublime, sublime_plugin
import re, string, os, sys, functools, mmap
from collections import Counter

sys.path.append(os.path.dirname(__file__))
import verilog_module

sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
import verilogutil
import sublimeutil


############################################################################
# Display type of the signal/variable under the cursor into the status bar #
class VerilogTypeCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        region = self.view.sel()[0]
        # If nothing is selected expand selection to word
        if region.empty() : region = self.view.word(region);
        v = self.view.substr(region)
        region = self.view.line(region)
        s = self.get_type(v,region.b)
        if s is None:
            s = "No definition found for " + v
        sublime.status_message(s)

    def get_type(self,var_name,pos):
        # select whole file
        txt = self.view.substr(sublime.Region(0, pos))
        # Extract type
        ti = verilogutil.get_type_info(txt,var_name)
        # print(ti)
        return ti['decl']

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
        sl = [r'\s*input\s+(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:]*\s+)?(\[[\w\:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?' + v + r'\b']
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
            print(txt[:500])
            m = re.search(r"(?s)^\s*(?P<type>module|interface)\s+(?P<name>\w+\b)",txt, re.MULTILINE)
            if not m:
                return
            print(m.groups())
            mname = m.group('name')
        else:
            mname = self.view.substr(self.view.sel()[0])
        projname = sublime.active_window().project_file_name()
        # TODO: make this async
        if projname not in verilog_module.list_module_files:
            verilog_module.VerilogModuleInstCommand.get_list_file(None,projname,None)
        inst_dict = {}
        cnt = 0
        for fn in verilog_module.list_module_files[projname]:
            f = open(fn)
            if os.stat(fn).st_size:
                txt = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                re_str = r'^(\s*'+mname+r'\s+(#\s*\(.*\)\s*)?(\w+).*$)'
                il = re.findall(str.encode(re_str),txt,re.MULTILINE)
                if il:
                    cnt += len(il)
                    inst_dict[fn] = il
        if inst_dict:
            v = sublime.active_window().new_file()
            # v.set_name('Find Results')
            v.set_name(mname + ' Instances')
            v.set_syntax_file('Packages/SystemVerilog/Find Results SV.hidden-tmLanguage')
            v.set_scratch(True)
            txt = mname + ': %0d instances.\n\n' %(cnt)
            for (name,il) in inst_dict.items():
                txt += name + ':\n'
                for i in il:
                    txt += '    - ' + str(i[2].decode().strip()) + '\n'
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
        words = re.findall(r'\w+',txt,re.MULTILINE)
        cnt = Counter(words)
        for s in sl:
            if cnt[s]==1 :
                if self.us:
                    self.us += ', '
                self.us += s
        self.sid = {x['name']:x for x in mi['signal'] if x['name'] in self.us}
        sl = self.us.split(', ')
        re_str = '('
        for i,s in enumerate(sl):
            re_str += r'\b'+s+r'\b'
            if i!=len(sl)-1:
                re_str+='|'
        re_str += ')'
        rl = self.view.find_all(re_str)
        self.view.sel().clear()
        self.view.sel().add_all(rl)
        if self.us:
            panel = sublime.active_window().show_input_panel("Unused signal to remove", self.us, self.on_prompt_done, None, None)

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

    def delete_comment_line(self,edit,r):
        r_tmp = self.view.full_line(r.a)
        m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
        if m:
            self.view.erase(edit,r_tmp)
