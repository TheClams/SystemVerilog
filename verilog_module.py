import sublime, sublime_plugin
import re, string, os, sys, functools, mmap, imp
import time, json

try:
    from SystemVerilog.verilogutil import verilogutil
    from SystemVerilog.verilogutil import sublimeutil
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "verilogutil"))
    import verilogutil
    import sublimeutil

list_module_files = {}
lmf_update_ongoing = False

def plugin_loaded():
    imp.reload(verilogutil)
    imp.reload(sublimeutil)
    fname = os.path.join(sublime.cache_path(),"systemverilog_lmf.json")
    # print('Cache file = {}'.format(fname))
    if os.path.isfile(fname) :
        global list_module_files
        list_module_files = json.load(open(fname))
        # print('Found list of modules files for projects {}'.format(list(list_module_files.keys())))



############################################################################
# Helper function: retrieve type info with support for import statement
def type_info(view,txt,varname):
    ti = verilogutil.get_type_info(txt,varname)
    if not ti or not ti['type']:
        ti = type_info_from_import(view,txt,varname)
    return ti

def type_info_file(view,fname,varname):
    ti = verilogutil.get_type_info_file(fname,varname)
    if not ti or not ti['type']:
        with open(fname) as f:
            flines = f.read()
            ti = type_info_from_import(view,flines,varname)
    return ti

def type_info_from_import(view,txt,varname):
    ti = {'decl':None,'type':None,'array':"",'bw':"", 'name':varname, 'tag':None, 'value':None}
    for m in re.finditer(r'\bimport\s+(.+?);',txt,flags=re.MULTILINE):
        for mp in re.finditer(r'\b(\w+)(\:\:[\w\*]+)+',m.groups()[0],flags=re.MULTILINE):
            pi = lookup_package(view,mp.groups()[0])
            # print('Package: {0} : {1}'.format(mp.groups()[0],pi))
            if pi:
                for x in pi['member']:
                    if x['name']==varname:
                        ti = x
                        break
        if ti['type']:
            break
    return ti

def type_info_from_base(view,r,varname):
    ti = None
    cname,cdecl,_ = sublimeutil.find_closest(view,r,r'(?s)\bclass\s+.*?\bextends\s+(.*?);')
    # print ('[SV: type_info_from_base] inside class {}'.format(cname))
    if cname:
        ci = lookup_type(view,cname)
        # print ('Extend class {0} : {1}'.format(cdecl,ci))
        if varname=='super':
            ti = ci
        elif ci and 'fname' in ci:
            fname = ci['fname'][0]
            ti = type_info_file(view,fname,varname)
            # print ('From base class, variable definition of "{0}" in file {1} : {2}'.format(varname,fname,ti))
            # Check a second level of parent class if not found
            if not ti['type'] and 'extend' in ci and ci['extend']:
                pos = ci['extend'].find('#')
                cdecl = ci['extend']
                cname = ci['extend'] if pos==-1 else ci['extend'][0:pos]
                ci = lookup_type(view,cname)
                # print ('Extend class {0} : {1}'.format(cname,ci))
                if ci and 'fname' in ci:
                    fname = ci['fname'][0]
                    ti = type_info_file(view,fname,varname)
                    # print ('From base class, variable definition of "{0}" in file {1} : {2}'.format(varname,fname,ti))
            # Check if the type is defined in the same file we found the signal declaration
            if ti['type']:
                tti = type_info_file(view,fname,ti['type'])
                if tti and tti['decl']:
                    # print ('From base class, type definition of "{0}" in file {1} : {2}'.format(ti['type'],fname,tti))
                    param_list = [] if 'param' not in ci else [x['name'] for x in ci['param']]
                    if tti['decl'].startswith('parameter') or tti['name'] in param_list:
                        # Check for parameter settings
                        m = re.search(r'#\s*\((.*)\)',cdecl)
                        param_set = m.groups()[0]
                        new_type = ''
                        # print('decl={} -> pram_set={}'.format(cdecl,param_set))
                        if param_set:
                            # by named connection
                            m = re.search(r'\.'+ti['type']+r'\((.*?)\)',param_set)
                            if m:
                                # print('Found parameter affectation by name: {0}'.format(m.groups()[0]))
                                new_type = m.groups()[0]
                            # if not by name check by position
                            else :
                                pos = -1
                                for p in ci['param']:
                                    if p['name']==ti['type']:
                                        pos = p['position']
                                        # print('found parameter {0} at position {1}'.format(ti['type'],pos))
                                        break
                                pl = re.sub(r'\(.*?\)','',param_set).split(',')
                                if pos >= 0 and pos <len(pl):
                                    new_type = pl[pos]
                            # Update type and declaration with the found type instead of the parameter name
                            if new_type:
                                ti['decl'] = ti['decl'].replace(ti['type'],new_type)
                                ti['type'] = new_type
    return ti


def type_info_on_hier(view,varname,txt=None,region=None):
    va = varname.split('.')
    ti = None
    scope = ''
    if not txt and region:
        txt = view.substr(sublime.Region(0, view.line(region).b))
    for i in range(0,len(va)):
        v = va[i].split('[')[0] # retrieve name without array part
        # Get type definition: first iteration is done inside current file
        if i==0:
            if region:
                scope = view.scope_name(region.a)
            ti = {'type':None}
            # If in a function body: check for a definition in the fubction first
            if 'meta.function.body' in scope:
                r_func = sublimeutil.expand_to_scope(view,'meta.function.body',region)
                ti = type_info(view,view.substr(r_func),varname)
            # Check in the whole text
            if not ti['type']:
                ti = type_info(view,txt,v)
            #if not found check for a definition in base class if this is an extended class
            if not ti['type'] and region:
                bti = type_info_from_base(view,region,ti['name'])
                if bti:
                    ti = bti
        elif ti and ti['type']:
            if ti['type']=='module':
                ti = lookup_module(view,ti['name'])
            elif ti['type']=='clocking' :
                for p in ti['port']:
                    if p['name']==v :
                        # Suppose we got here through a lookup (TBC if it is always the case)
                        if fname:
                            ti = ti = type_info_file(view,fname,v)
                        else :
                            ti = p['name']
                            ti['decl'] = '{} logic {}'.format(ti['type'],v)
                        break;
                else : # not found
                    ti = None
            elif ti['type']!='class':
                # print ('[type_info_on_hier] Looking for type {}'.format(ti))
                ti = lookup_type(view,ti['type'])
                if ti and ti['type']:
                    if ti['tag']=='typedef':
                        bti = lookup_type(view,ti['type'])
                        if bti:
                            ti = bti

        # Lookup for the variable inside the type defined
        if not ti:
            return None
        if ti['type']=='struct' :
            m = re.search(r'\{(.*)\}', ti['decl'])
            til = verilogutil.get_all_type_info(m.groups()[0])
            ti = None
            for e in til:
                if e['name']==v:
                    ti = e
                    break
        elif 'fname' in ti:
            fname = ti['fname'][0]
            ti = type_info_file(view,fname,v)
            if ti['type'] in ['function', 'task']:
                with open(fname) as f:
                    flines = verilogutil.clean_comment(f.read())
                ti = verilogutil.parse_function(flines,v)
        # print ('[type_info_on_hier] => type info of {0} = {1}'.format(v,ti))
    return ti

########################################
def lookup_module(view,mname):
    mi = None
    filelist = view.window().lookup_symbol_in_index(mname)
    if filelist:
        # Check if module is defined in current file first
        fname = view.file_name()
        flist_norm = [sublimeutil.normalize_fname(f[0]) for f in filelist]
        if fname in flist_norm:
            _,_,rowcol = filelist[flist_norm.index(fname)]
            mi = verilogutil.parse_module_file(fname,mname)
        if mi:
            mi['fname'] = (fname,rowcol[0],rowcol[1])
        # Consider first file with a valid module definition to be the correct one
        else:
            for f in filelist:
                fname, display_fname, rowcol = f
                fname = sublimeutil.normalize_fname(fname)
                mi = verilogutil.parse_module_file(fname,mname)
                if mi:
                    mi['fname'] = (fname,rowcol[0],rowcol[1])
                    break
    # print('[SV:lookup_module] {0}'.format(mi))
    return mi

def lookup_package(view,pkgname):
    pi = None
    mi = None
    filelist = view.window().lookup_symbol_in_index(pkgname)
    if filelist:
        # Check if module is defined in current file first
        fname = view.file_name()
        flist_norm = [sublimeutil.normalize_fname(f[0]) for f in filelist]
        if fname in flist_norm:
            _,_,rowcol = filelist[flist_norm.index(fname)]
            mi = verilogutil.parse_package_file(fname,pkgname)
        # Consider first file with a valid module definition to be the correct one
        if mi:
            pi = {'type': 'package', 'member': mi, 'fname':(fname,rowcol[0],rowcol[1])}
        else:
            for f in filelist:
                fname, display_fname, rowcol = f
                fname = sublimeutil.normalize_fname(fname)
                mi = verilogutil.parse_package_file(fname,pkgname)
                if mi:
                    pi = {'type': 'package', 'member': mi, 'fname':(fname,rowcol[0],rowcol[1])}
                    break
    # print('[SV:lookup_package] {0}'.format(pi))
    return pi

def lookup_function(view,funcname):
    fi = None
    filelist = view.window().lookup_symbol_in_index(funcname)
    # print('Files for {0} = {1}'.format(funcname,filelist))
    if filelist:
        # Check if function is defined in current file first
        fname = view.file_name()
        flist_norm = [sublimeutil.normalize_fname(f[0]) for f in filelist]
        if fname in flist_norm:
            _,_,rowcol = filelist[flist_norm.index(fname)]
            with open(fname,'r') as f:
                flines = str(f.read())
            flines = verilogutil.clean_comment(flines)
            fi = verilogutil.parse_function(flines,funcname)
        if fi:
            fi['fname'] = (fname,rowcol[0],rowcol[1])
        # Consider first file with a valid function definition to be the correct one
        else:
            for f in filelist:
                fname, display_fname, rowcol = f
                fname_ = sublimeutil.normalize_fname(fname)
                with open(fname_,'r') as f:
                    flines = str(f.read())
                flines = verilogutil.clean_comment(flines)
                fi = verilogutil.parse_function(flines,funcname)
                if fi:
                    # rowcols = [x for fn,_,x in filelist if fn==fname_]
                    fi['fname'] = (fname_,rowcol[0],rowcol[1])
                    break
    return fi

def lookup_type(view, t):
    ti = None
    pkg_fl = []
    if '::' in t:
        ts = t.split('::')
        pkg_fl = view.window().lookup_symbol_in_index(ts[0])
        #print('[lookup_type] Package {} defined in {}'.format(ts[0],pkg_fl))
        # Try to retrieve package filename
        t = ts[-1]
    filelist = view.window().lookup_symbol_in_index(t)
    if pkg_fl :
        fl = []
        fl_name = [x[0] for x in filelist]
        filelist = [x for x in pkg_fl if x[0] in fl_name]
    if filelist:
        # Check if symbol is defined in current file first
        fname = view.file_name()
        flist_norm = [sublimeutil.normalize_fname(f[0]) for f in filelist]
        if fname in flist_norm:
            _,_,rowcol = filelist[flist_norm.index(fname)]
            # print(t + ' defined in current file' + str(fname))
            ti = type_info_file(view,fname,t)
        if ti and ti['type'] and ti['tag']!='typedef' :
            ti['fname'] = (fname,rowcol[0],rowcol[1])
        # Consider first file with a valid type definition to be the correct one
        else:
            settings = view.settings()
            file_ext = tuple(settings.get('sv.v_ext','v') + settings.get('sv.sv_ext','sv') + settings.get('sv.vh_ext','vh') + settings.get('sv.svh_ext','svh'))
            for f in filelist:
                fname, display_fname, rowcol = f
                fname = sublimeutil.normalize_fname(fname)
                if fname.lower().endswith(file_ext):
                    ti = type_info_file(view,fname,t)
                    if ti['type'] and ti['tag']!='typedef' :
                        ti['fname'] = (fname,rowcol[0],rowcol[1])
                        break
    # print('[SV:lookup_type] {0}'.format(ti))
    return ti

def lookup_macro(view, name):
    txt = ''
    params = []
    filelist = view.window().lookup_symbol_in_index(name)
    if filelist:
        fname = view.file_name()
        # Check if symbol is defined in current file first
        if fname in [sublimeutil.normalize_fname(f[0]) for f in filelist]:
            with open(fname,'r') as f:
                flines = str(f.read())
            txt,params = verilogutil.get_macro(flines,name)
        else:
            for fi in filelist:
                fname = sublimeutil.normalize_fname(fi[0])
                with open(fname,'r') as f:
                    flines = str(f.read())
                txt,params = verilogutil.get_macro(flines,name)
                if txt:
                    break
    return txt,params


########################################
# Create module instantiation skeleton #
class VerilogModuleInstCommand(sublime_plugin.TextCommand):

    #TODO: Run the search in background and keep a cache to improve performance
    def run(self,edit):
        global list_module_files
        if len(self.view.sel())>0 :
            r = self.view.sel()[0]
            scope = self.view.scope_name(r.a)
            if 'meta.module.inst' in scope:
                self.view.run_command("verilog_module_reconnect")
                return
        self.window = sublime.active_window()
        # Populate the list_module_files:
        #  - If no folder in current project, just list open files
        #  - if it exist use latest version and display panel immediately while running an update
        #  - if not display panel only when list is ready
        projname = self.window.project_file_name()
        if not sublime.active_window().folders():
            list_module_files['__NONE__'] = []
            for v in self.window.views():
                if v and v.file_name():
                    list_module_files['__NONE__'].append(os.path.abspath(v.file_name()))
            self.on_list_done('__NONE__')
        elif projname not in list_module_files:
            sublime.set_timeout_async(functools.partial(self.get_list_file,projname,functools.partial(self.on_list_done,projname)), 0)
            sublime.status_message('Please wait while module list is being built')
        else:
            # Create a copy so that the background update does not change the content of the list
            list_module_files['__COPY__'] = list_module_files[projname][:]
            # Start background update of the list
            if not lmf_update_ongoing :
                sublime.set_timeout_async(functools.partial(self.get_list_file,projname), 0)
            # Display quick panel
            self.on_list_done('__COPY__')

    def get_list_file(self, projname, callback=None):
        global list_module_files
        global lmf_update_ongoing
        lmf_update_ongoing = True
        lmf = []
        settings = self.view.settings()
        file_ext = tuple(settings.get('sv.v_ext','v') + settings.get('sv.sv_ext','sv'))
        lf = []
        t0 = time.time()
        for folder in sublime.active_window().folders():
            for root, dirs, files in os.walk(folder):
                for fn in files:
                    if fn.lower().endswith(file_ext):
                        ffn = os.path.join(root,fn)
                        lf.append(ffn)
        # print('Directory scanning done after {}s. Start scanning {} files'.format(int(time.time() - t0), len(lf)))
        for ffn in lf :
            try :
                f = open(ffn)
                if os.stat(ffn).st_size:
                    s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                    if s.find(b'module') != -1:
                        lmf.append(ffn)
            # Silently discard opening file
            except :
                pass
        # print('List of module files updated in {}s'.format(int(time.time() - t0)))
        list_module_files[projname] = lmf[:]
        #
        fname = os.path.join(sublime.cache_path(),"systemverilog_lmf.json")
        with open(fname,'wb') as f:
            f.write(json.dumps(list_module_files).encode('UTF-8'))
        lmf_update_ongoing = False
        if callback:
            callback()

    def on_list_done(self,projname):
        self.window.show_quick_panel(list_module_files[projname], functools.partial(self.on_select_file_done,projname))

    def on_select_file_done(self, projname, index):
        if index >= 0:
            fname = list_module_files[projname][index]
            try:
                with open(fname, "r") as f:
                    flines = str(f.read())
                self.ml=re.findall(r'^\s*module\s+(\w+)',flines,re.MULTILINE);
                if len(self.ml)<2:
                    self.view.run_command("verilog_do_module_parse", {"args":{'fname': fname, 'mname':r'\w+'}})
                else:
                    sublime.set_timeout_async(lambda: self.window.show_quick_panel(self.ml, functools.partial(self.on_select_module_done,fname)),0)
            except FileNotFoundError:
                print('[VerilogModule.Instance] File not found ')

    def on_select_module_done(self, fname, index):
        if index >= 0:
            self.view.run_command("verilog_do_module_parse", {"args":{'fname': fname, 'mname':self.ml[index]}})

class VerilogDoModuleParseCommand(sublime_plugin.TextCommand):

    def run(self, edit, args):
        self.fname = args['fname']
        #TODO: check for multiple module in the file
        settings = self.view.settings()
        self.pm = verilogutil.parse_module_file(self.fname, args['mname'],no_inst=True)
        self.param_explicit = settings.get('sv.param_explicit',False)
        self.param_propagate = settings.get('sv.param_propagate',False)
        # print(self.pm)
        if self.pm is not None:
            self.param_value = []
            if self.pm['param'] and settings.get('sv.fillparam'):
                self.cnt = 0
                self.show_prompt()
            else:
                if self.param_explicit :
                    for x in self.pm['param'] :
                        self.param_value.append({'name':x['name'] , 'value': x['value']});
                self.view.run_command("verilog_do_module_inst", {"args":{'pm':self.pm, 'pv':self.param_value, 'text':self.fname}})

    def on_prompt_done(self, content):
        if not content.startswith("Default"):
            self.param_value.append({'name':self.pm['param'][self.cnt]['name'] , 'value': content});
        elif self.param_explicit :
            self.param_value.append({'name':self.pm['param'][self.cnt]['name'] , 'value': content[9:]});
        self.cnt += 1
        if not self.pm['param']:
            return
        if self.cnt < len(self.pm['param']):
            self.show_prompt()
        else:
            self.view.run_command("verilog_do_module_inst", {"args":{'pm':self.pm, 'pv':self.param_value, 'text':self.fname}})

    def show_prompt(self):
        p = self.pm['param'][self.cnt]
        if self.param_propagate:
            default = 'parameter '
            if p['decl']:
                default += p['decl'] + ' '
            default += '{0} = {1}'.format(p['name'],p['value'])
        else:
            default = 'Default: {0}'.format(p['value'])
        panel = sublime.active_window().show_input_panel(p['name'], default, self.on_prompt_done, None, None)
        #select the whole line (to ease value change)
        r = panel.line(panel.sel()[0])
        panel.sel().clear()
        panel.sel().add(r)


class VerilogDoModuleInstCommand(sublime_plugin.TextCommand):
    #TODO: check base indentation
    def run(self, edit, args):
        settings = self.view.settings()
        isAutoConnect = settings.get('sv.autoconnect',False)
        isParamOneLine = settings.get('sv.param_oneline',True)
        isInstOneLine = settings.get('sv.inst_oneline',True)
        isColumnAlignment = settings.get('sv.param_port_alignment',True)
        indent_level = settings.get('sv.decl_indent')
        param_decl = ''
        pm = args['pm']
        # print(pm)
        # Update Module information with parameter value for later signal declaration using correct type
        for p in args['pv']:
            for pmp in pm['param']:
                if pmp['name']==p['name']:
                    if p['value'].startswith('parameter') or p['value'].startswith('localparam'):
                        pmp['value']= p['name']
                        param_decl +=  indent_level*'\t' + p['value'] + ';\n'
                        m = re.search(r"(?P<name>\w+)\s*=",p['value'])
                        p['value'] = m.group('name')
                    else:
                        pmp['value']=p['value']
                    break
        # print('[VerilogDoModuleInstCommand] pm = '+ str(pm))
        decl = ''
        ac = {}
        wc = {}
        # Add signal port declaration
        if isAutoConnect and pm['port']:
            (decl,ac,wc) = self.get_connect(self.view, settings, pm)
            #Find location where to insert signal declaration: default to just before module instantiation
            if decl or param_decl:
                r = self.get_region_decl(self.view,settings)
                self.view.insert(edit, r, '\n'+param_decl+decl)
                sublime.status_message('Adding ' + str(len(decl.splitlines())) + ' signals declaration' )
        inst_name = settings.get('sv.instance_prefix','') + pm['name'] + settings.get('sv.instance_suffix','')
        # Check if instantiation can fit on one line only
        if isInstOneLine :
            len_inst = len(pm['name']) + 1 + len(inst_name) + 2
            if len(args['pv']) > 0:
                len_inst += 2
                for p in args['pv']:
                    len_inst += len(p['name']) + len(p['value']) + 5
            if len_inst+3 > settings.get('sv.max_line_length',120):
                isParamOneLine = False
            elif pm['port']:
                for p in pm['port']:
                    len_inst += len(p['name']) + 5
                    if p['name'] in ac.keys():
                        len_inst+= len(ac[p['name']])
                    else :
                        len_inst+= len(p['name'])
            if len_inst+3 > settings.get('sv.max_line_length',120):
                isInstOneLine = False
        # Instantiation
        inst = pm['name'] + " "
        # Parameters: bind only parameters for which a value different from default was set
        if len(args['pv']) > 0:
            if isParamOneLine or not isColumnAlignment:
                max_len = 0
            else:
                max_len = max([len(x['name']) for x in args['pv']])
            inst += "#("
            if not isParamOneLine:
                inst += "\n"
            for i in range(len(args['pv'])):
                if not isParamOneLine:
                    inst += "\t"
                inst+= "." + args['pv'][i]['name'].ljust(max_len) + "("+args['pv'][i]['value']+")"
                if i<len(args['pv'])-1:
                    inst+=","
                if not isParamOneLine:
                    inst+="\n"
                elif i<len(args['pv'])-1:
                    inst+=" "
            inst += ") "
        #Port binding
        inst +=  inst_name + " ("
        if not isInstOneLine:
             inst+="\n"
        if pm['port']:
            # Get max length of a port to align everything
            if isInstOneLine or not isColumnAlignment:
                max_len_p = 0
                max_len_s = 0
            else :
                max_len_p = max([len(x['name']) for x in pm['port']])
                max_len_s = max_len_p
            # print('Autoconnect dict = ' + str([ac[x] for x in ac]))
                if len(ac)>0 :
                    max_len_s = max([len(ac[x]) for x in ac])
                    if max_len_p>max_len_s:
                        max_len_s = max_len_p
            for i in range(len(pm['port'])):
                portname = pm['port'][i]['name']
                if not isInstOneLine:
                    inst += "\t"
                inst+= "." + portname.ljust(max_len_p) + "("
                if isAutoConnect:
                    if portname in ac.keys():
                        inst+= ac[portname].ljust(max_len_s)
                    else :
                        inst+= portname.ljust(max_len_s)
                inst+= ")"
                if i<len(pm['port'])-1:
                    inst+=","
                if not isInstOneLine:
                    if portname in wc.keys():
                        inst+=" // TODO: Check connection ! " + wc[portname]
                    inst+="\n"
                elif i<len(pm['port'])-1:
                    inst+=" "
        inst += ");\n"
        self.view.insert(edit, self.view.sel()[0].a, inst)
        # Status report
        nb_decl = len(decl.splitlines())
        s = ''
        if nb_decl:
            s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)\n'
        if len(ac)>0 :
            s+= 'Non-perfect name match for ' + str(len(ac)) + ' port(s) : ' + str(ac) + '\n'
        if len(wc)>0 :
            s+= 'Found ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()]) + '\n'
        if s!='':
            sublimeutil.print_to_panel(s,'SystemVerilog')

    def get_region_decl(self, view, settings, r=None):
        if not r:
            r = view.sel()[0].begin()
        s = settings.get('sv.decl_start','')
        if s!='' :
            r_start = view.find(s,0,sublime.LITERAL)
            if r_start :
                s = settings.get('sv.decl_end','')
                r_stop = None
                if s!='':
                    r_stop = view.find(s,r_start.a,sublime.LITERAL)
                # Find first empty Find line
                if r_stop:
                    r_tmp = view.find_by_class(r_stop.a,False,sublime.CLASS_EMPTY_LINE)
                else :
                    r_tmp = view.find_by_class(r_start.a,True,sublime.CLASS_EMPTY_LINE)
                if r_tmp:
                    r = r_tmp
        return r

    def get_connect(self,view,settings,pm):
        # Init return variable
        decl = ""
        ac = {} # autoconnection (entry is port name)
        wc = {} # warning connection (entry is port name)
        # get settings
        port_prefix = settings.get('sv.autoconnect_port_prefix', [])
        port_suffix = settings.get('sv.autoconnect_port_suffix', [])
        indent_level = settings.get('sv.decl_indent', 1)
        #default signal type to logic, except verilog file use wire (if type is implicit)
        fname = view.file_name()
        sig_type = 'logic'
        if fname: # handle case where view is a scratch buffer and has no filename
            if fname.endswith('.v'):
                sig_type = 'wire'
        # read file to be able to check existing declaration
        flines = view.substr(sublime.Region(0, view.size()))
        mi = verilogutil.parse_module(flines,no_inst=True)
        if not mi:
            print('[VerilogModule.get_connect] Unable to parse current module')
            return (decl,ac,wc)
        signal_dict = {}
        for ti in mi['port']:
            signal_dict[ti['name']] = ti
        for ti in mi['signal']:
            signal_dict[ti['name']] = ti
        # print ('Signal Dict = ' + str(signal_dict))
        signal_dict_text = ''
        for (name,ti) in signal_dict.items():
            signal_dict_text += name+'\n'
        # print ('Signal name list = ' + signal_dict_text)
        if pm['param']:
            param_dict = {p['name']:p['value'] for p in pm['param']}
        else:
            param_dict = {}
        # print(param_dict)
        # Add signal declaration
        for p in pm['port']:
            pname = p['name']
            #Remove suffix/prefix of port name
            for prefix in port_prefix:
                if pname.startswith(prefix):
                    pname = pname[len(prefix):]
                    break
            for suffix in port_suffix:
                if pname.endswith(suffix):
                    pname = pname[:-len(suffix)]
                    break
            if pname!=p['name']:
                ac[p['name']] = pname
            #check existing signal declaration and coherence
            ti = {'decl':None,'type':None,'array':"",'bw':"", 'name':pname, 'tag':''}
            if pname in signal_dict:
                ti = signal_dict[pname]
            # Get signal declaration for the port
            if p['decl'] :
                p['declSig'] = re.sub(r'input |output |inout ','',p['decl']) # remove I/O indication
                p['declSig'] = re.sub(r'var ','',p['declSig']) # remove var indication
                p['declSig'] = re.sub(r'\b'+p['name']+r'\b',pname,p['declSig']) # Remove prefix/suffix
                if p['type'].startswith(('input','output','inout')) :
                    p['declSig'] = sig_type + ' ' + p['declSig']
                elif '.' in p['declSig']: # For interface remove modport and add instantiation. (No support for autoconnection of interface)
                    p['declSig'] = re.sub(r'(\w+)\.\w+\s+(.*)',r'\1 \2()',p['declSig'])
                # Replace reg by sigtype for output port
                if p['decl'].startswith('output') and re.search(r'\breg\b',p['decl']):
                    if re.search(r'\b'+sig_type+r'\b',p['decl']):
                        p['declSig'] = re.sub(r'\breg\s+','',p['declSig'])
                    else:
                        p['declSig'] = re.sub(r'\breg\b',sig_type,p['declSig'])
                for (k,v) in param_dict.items():
                    if k in p['declSig']:
                        p['declSig'] = re.sub(r'\b'+k+r'\b',v,p['declSig'])
                # try to cleanup the array size: [16-1:0] should give a proper [15:0]
                # Still very basic, but should be ok for most cases
                fa = re.findall(r'((\[|:)\s*(\d+)\s*(\+|-)\s*(\d+))',p['declSig'])
                for f in fa:
                    if f[3]=='+':
                        value = int(f[2])+int(f[4])
                    else:
                        value = int(f[2])-int(f[4])
                    p['declSig'] = p['declSig'].replace(f[0],f[1]+str(value))
            # Check for extended match : prefix
            if ti['decl'] is None:
                if settings.get('sv.autoconnect_allow_prefix',False):
                    for m in re.finditer(r'\b(\w+_'+pname+r')\b', signal_dict_text, flags=re.MULTILINE):
                        if m.group(0) in signal_dict:
                            ti = signal_dict[m.group(0)]
                            if ti['decl']:
                                # Do a coherence check and reset the declaration if it does not match (to be sure we continue searching for it)
                                match,_ = check_connect(p,ti)
                                if match:
                                    if m.group(0) != p['name']:
                                        ac[p['name']] = m.group(0)
                                    break
                                else:
                                    ti = {'decl':None,'type':None,'array':"",'bw':"", 'name':pname, 'tag':''}
            # Check for extended match : suffix
            if ti['decl'] is None:
                if settings.get('sv.autoconnect_allow_suffix',False):
                    for m in re.finditer(r'\b('+pname+r'_\w+)\b', signal_dict_text, flags=re.MULTILINE):
                        if m.group(0) in signal_dict:
                            ti = signal_dict[m.group(0)]
                            if ti['decl']:
                                # Do a coherence check and reset the declaration if it does not match (to be sure we continue searching for it)
                                match,_ = check_connect(p,ti)
                                if match:
                                    if m.group(0) != p['name']:
                                        ac[p['name']] = m.group(0)
                                    break
                                else:
                                    ti = {'decl':None,'type':None,'array':"",'bw':"", 'name':pname, 'tag':''}
            # Get declaration of signal for connecteion
            if p['decl'] :
                # If no signal is found, add declaration
                if ti['decl'] is None:
                    # print ("Adding declaration for " + pname + " => " + str(p['decl'] + ' => ' + d))
                    decl += indent_level*'\t' + p['declSig'] + ';\n'
                # Else check signal coherence
                else :
                    # print('[get_connect] signal={} -- port={}'.format(ti['decl'],p['decl']))
                    match,warn = check_connect(p,ti)
                    if not match :
                        wc[p['name']] = warn
                        # print(wc[p['name']])
        return (decl,ac,wc)

def check_connect(port,sig):
    # print('Check {} vs {}'.format(port['decl'],sig['decl']))
    # Check port direction
    if sig['decl'].startswith('input') and not port['decl'].startswith('input'):
        return False,'Incompatible port direction (not an input)'
    # elif sig['decl'].startswith('output') and not port['decl'].startswith('output'):
    #     wc[port['name']] = 'Incompatible port direction (not an output)'
    elif sig['decl'].startswith('inout') and not port['decl'].startswith('inout'):
        return False,'Incompatible port direction not an inout'
    # check type
    ds = re.sub(r'input |output |inout ','',sig['decl']) # remove I/O indication
    # remove qualifier like var, signed, unsigned indication
    ds = re.sub(r'var |signed |unsigned ','',ds.strip())
    d  = re.sub(r'signed |unsigned ','',port['declSig'])
    # remove () for interface
    if '$' not in d:
        d = re.sub(r'\(|\)','',d)
    if sig['type'].startswith(('input','output','inout')) and not ds.startswith('logic '):
        ds = 'logic ' + ds
    elif '.' in ds: # For interface remove modport
        ds = re.sub(r'(\w+)\b(.*)',r'\1',ds)
        d = re.sub(r'(\w+)\b(.*)',r'\1',d)
    # convert wire/reg to logic
    ds = re.sub(r'\b(wire|reg)\b','logic',ds.strip())
    d  = re.sub(r'\b(wire|reg)\b','logic',d.strip())
    # Remove scope if not available in both type
    if ('::' in ds and '::' not in d) or ('::' not in ds and '::' in d) :
        ds = re.sub(r'\w+\:\:','',ds)
        d = re.sub(r'\w+\:\:','',d)
    # In case of smart autoconnect replace the signal name by the port name
    # if port['name'] in ac.keys():
    #     ds = re.sub(r'\b' + ac[port['name']] + r'\b', pname,ds)
    if sig['name'] != port['name']:
        ds = re.sub(r'\b' + sig['name'] + r'\b', port['name'],ds)
    if ds!=d :
        warn = 'Signal/port not matching : Expecting ' + d + ' -- Found ' + ds
        return False,re.sub(r'\b'+port['name']+r'\b','',warn) # do not display port name
    return True,''

##########################################
# Toggle between .* and explicit binding #
class VerilogDoToggleDotStarCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        r = self.view.sel()[0]
        scope = self.view.scope_name(r.a)
        if 'meta.module.inst' not in scope:
            return
        # Select whole module instantiation
        r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
        txt = verilogutil.clean_comment(self.view.substr(r))
        #Extract existing binding
        bl = re.findall(r'(?s)\.(\w+)\s*\(\s*(.*?)\s*\)',txt,flags=re.MULTILINE)
        #
        if '.*' in txt:
            # Parse module definition
            mname = re.findall(r'\w+',txt)[0]
            filelist = self.view.window().lookup_symbol_in_index(mname)
            if not filelist:
                return
            for f in filelist:
                fname = sublimeutil.normalize_fname(f[0])
                mi = verilogutil.parse_module_file(fname,mname,no_inst=True)
                if mi:
                    break
            if not mi:
                return
            dot_star = ''
            b0 = [x[0] for x in bl]
            for p in mi['port']:
                if p['name'] not in b0:
                    dot_star += '.' + p['name']+'('+p['name']+'),\n'
            # select the .* and replace it (exclude the two last character which are ',\n')
            if dot_star != '' :
                r_tmp = self.view.find(r'\.\*',r.a)
                self.view.replace(edit,r_tmp,dot_star[:-2])
            else : # case where .* was superfluous (all bindings were manual) : remove .* including the potential ,
                r_tmp = self.view.find(r'\.\*\s*(,)?',r.a)
                self.view.erase(edit,r_tmp)
        else:
            # Find beginning of the binding and insert the .*
            r_begin = self.view.find(r'(\w+|\))\b\s*\w+\s*\(',r.a)
            if r.contains(r_begin):
                cnt = 0
                # erase all binding where port and signal have same name
                for b in bl:
                    if b[0]==b[1]:
                        cnt = cnt + 1
                        r_tmp = self.view.find(r'\.'+b[0]+r'\s*\(\s*' + b[0] + r'\s*\)\s*(,)?',r.a)
                        if r.contains(r_tmp):
                            self.view.erase(edit,r_tmp)
                            r_tmp = self.view.full_line(r_tmp.a)
                            m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
                            if m:
                                self.view.erase(edit,r_tmp)
                # Insert .* only if something was removed. Add , if not all binding were removed
                if cnt > 0:
                    if cnt==len(bl):
                        self.view.insert(edit,r_begin.b,'.*')
                    else :
                        self.view.insert(edit,r_begin.b,'.*,')
        self.view.run_command("verilog_align")

class VerilogToggleDotStarCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        r = self.view.sel()[0]
        scope = self.view.scope_name(r.a)
        if 'meta.module.inst' not in scope: # Not inside a module ? look for all .* inside a module instance and expand them
            ra = self.view.find_all(r'\.\*',0)
            for r in reversed(ra):
                scope = self.view.scope_name(r.a)
                if 'meta.module.inst' in scope:
                    self.view.sel().clear()
                    self.view.sel().add(r)
                    self.view.run_command("verilog_do_toggle_dot_star")
        else :
            self.view.run_command("verilog_do_toggle_dot_star")

############################
# Do a module reconnection #
class VerilogModuleReconnectCommand(sublime_plugin.TextCommand):

    def run(self,edit):
        if len(self.view.sel())==0 : return;
        r = self.view.sel()[0]
        scope = self.view.scope_name(r.a)
        if 'meta.module.inst' not in scope:
            return
        # Select whole module instantiation
        r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
        if self.view.classify(r.a) & sublime.CLASS_LINE_START == 0:
            r.a = self.view.find_by_class(r.a,False,sublime.CLASS_LINE_START)
        # print(self.view.substr(r))
        txt = verilogutil.clean_comment(self.view.substr(r))
        # Parse module definition
        mname = re.findall(r'\w+',txt)[0]
        filelist = self.view.window().lookup_symbol_in_index(mname)
        if not filelist:
            return
        for f in filelist:
            fname = sublimeutil.normalize_fname(f[0])
            mi = verilogutil.parse_module_file(fname,mname,no_inst=True)
            if mi:
                break
        if not mi:
            sublime.status_message('Unable to retrieve module information for ' + mname)
            return
        settings = self.view.settings()
        mpl = [x['name'] for x in mi['port']]
        mpal = [x['name'] for x in mi['param']]
        #Extract existing binding
        bl = re.findall(r'(?s)\.(\w+)\s*\(\s*(.*?)\s*\)\s*(,|\))',txt,flags=re.MULTILINE)
        # Handle case of binding by position (TODO: support parameter as well ...)
        if not bl:
            m = re.search(r'(?s)(#\s*\((?P<params>.*?)\)\s*)?\s*\w+\s*\((?P<ports>.*?)\)\s*;',txt,flags=re.MULTILINE)
            pl = m.group('ports')
            if pl:
                pa = pl.split(',')
                bt = ''
                for i,p in enumerate(pa):
                    if i >= len(mpl):
                        break;
                    bl.append((mpl[i],p.strip()))
                    bt += '.{portName}({sigName}),\n'.format(portName=bl[-1][0], sigName=bl[-1][1])
                # Replace connection by position by connection by name
                r_tmp = self.view.find(pl,r.a,sublime.LITERAL)
                if r.contains(r_tmp):
                    self.view.replace(edit,r_tmp,bt)
                    # Update region
                    r = sublimeutil.expand_to_scope(self.view,'meta.module.inst',r)
        ipl = [x[0] for x in bl]
        # Check for added port
        apl = [x for x in mpl if x not in ipl]
        if apl:
            (decl,ac,wc) = VerilogDoModuleInstCommand.get_connect(self, self.view, settings, mi)
            last_char = self.view.substr(sublime.Region(r.a,r.b-2)).strip(' \t')[-1]
            b = '\n' if last_char!='\n' else ''
            for p in apl:
                b+= "." + p + "("
                if p in ac.keys():
                    b+= ac[p]
                else :
                    b+= p
                b+= "),"
                if p in wc.keys():
                    b+=" // TODO: Check connection ! " + wc[p]
                b+="\n"
            # Add binding at the end of the instantiation
            self.view.insert(edit,r.b-2,b)
        # Check for deleted port
        dpl = [x for x in ipl if x not in mpl and x not in mpal]
        for p in dpl:
            r_tmp = self.view.find(r'(?s)\.'+p+r'\s*\(.*?\)\s*(,|\)\s*;)',r.a)
            if r.contains(r_tmp):
                s = self.view.substr(r_tmp)
                if s[-1]==';':
                    s_tmp = s[:-1].strip()[:-1]
                    r_tmp.b -= (len(s) - len(s_tmp))
                self.view.erase(edit,r_tmp)
                r_tmp = self.view.full_line(r_tmp.a)
                # cleanup comment
                m = re.search(r'^\s*(\/\/.*)?$',self.view.substr(r_tmp))
                if m:
                    self.view.erase(edit,r_tmp)
        # Print status
        # print('[reconnect] Module   Port list = ' + str(mpl))
        # print('[reconnect] Instance Port list = ' + str(ipl))
        # print('[reconnect]  => Removed Port list = ' + str(dpl))
        # print('[reconnect]  => Added   Port list = ' + str(apl))
        s =''
        if dpl:
            s += "Removed %d ports: %s\n" %(len(dpl),str(dpl))
        if apl:
            s += "Added %d ports: %s\n" %(len(apl),str(apl))
            decl_clean = ''
            ac_clean = {}
            for p in apl:
                if p in ac:
                    ac_clean[p] = ac[p]
                m = re.search(r'^.*\b'+p+r'\b.*;',decl, re.MULTILINE)
                if m:
                    decl_clean += m.group(0) +'\n'
            for p in ipl:
                if p in wc:
                    wc.pop(p)
            nb_decl = len(decl_clean.splitlines())
            if decl_clean:
                r_start = VerilogDoModuleInstCommand.get_region_decl(self, self.view,settings,r.a)
                self.view.insert(edit, r_start, '\n'+decl_clean)
                s+= 'Adding ' + str(nb_decl) + ' signal(s) declaration(s)\n'
            if len(ac_clean)>0 :
                s+= 'Non-perfect name match for ' + str(len(ac_clean)) + ' port(s) : ' + str(ac_clean) + '\n'
            if len(wc)>0 :
                s+= 'Found ' + str(len(wc)) + ' mismatch(es) for port(s): ' + str([x for x in wc.keys()]) +'\n'
        if s:
            sublimeutil.print_to_panel(s,'SystemVerilog')
        # Realign
        self.view.run_command("verilog_align")
