import sublime
import re, os, mmap, time, json, functools
from pathlib import Path

from . import verilogutil
from . import sublimeutil

############################################################################
# Cache of the files containing a module, per project
list_module_files = {}
lmf_update_ongoing = False

def _cache_fname():
    return os.path.join(sublime.cache_path(),"systemverilog_lmf.json")

def load_list_cache():
    """Load the list of module files from the cache file (in place)"""
    fname = _cache_fname()
    if os.path.isfile(fname) :
        with open(fname) as f:
            lmf = json.load(f)
        list_module_files.clear()
        list_module_files.update(lmf)

def get_list_file(view, projname, callback=None):
    """Scan the project folders to find all files containing a module and update the cache"""
    global lmf_update_ongoing
    lmf_update_ongoing = True
    lmf = []
    settings = view.settings()
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
    with open(_cache_fname(),'wb') as f:
        f.write(json.dumps(list_module_files).encode('UTF-8'))
    lmf_update_ongoing = False
    if callback:
        callback()

############################################################################
# Helper function: retrieve type info with support for import statement
def type_info(view,txt,varname):
    ti = verilogutil.get_type_info(txt,varname)
    if not ti or not ti['type'] or ti['type'] in ['var']:
        ti = type_info_from_import(view,txt,varname)
        if ti['decl'] is None:
            ti = type_info_from_include(view,txt,varname)
    return ti

def type_info_file(view,fname,varname):
    if fname.startswith('<') :
        v = view.window().find_open_file(fname)
        if v:
            txt = v.substr(sublime.Region(0,v.size()))
            return type_info(v,txt,varname)
    ti = verilogutil.get_type_info_file(fname,varname)
    if not ti or not ti['type']:
        with open(fname, 'r', encoding='utf-8') as f:
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

def type_info_from_include(view,txt,varname):
    sv_settings = sublime.load_settings('SystemVerilog.sublime-settings')
    search_incl = sv_settings.get('sv.search_incl', False) if sv_settings else False
    for m in re.finditer(r'`include\s+"(.+?)"',txt,flags=re.MULTILINE):
        fname = m.group(1)
        if os.path.exists(fname):
            ti = verilogutil.get_type_info_file(fname,varname)
        elif search_incl:
            full_path = ''
            for folder in sublime.active_window().folders():
                for full_path in Path(folder).rglob(fname):
                    ti = verilogutil.get_type_info_file(str(full_path),varname)
                    if ti['type']:
                        return ti
        if ti['type']:
            return ti
    # Not found
    return {'decl':None,'type':None,'array':"",'bw':"", 'name':varname, 'tag':None, 'value':None}

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
    fname = ''
    if not txt and region:
        txt = view.substr(sublime.Region(0, view.line(region).b))
    for i in range(0,len(va)):
        loc = ti['fname'] if ti and 'fname' in ti else None
        v = va[i].split('[')[0] # retrieve name without array part
        # Get type definition: first iteration is done inside current file
        if i==0:
            if region:
                scope = view.scope_name(region.a)
            ti = {'type':None}
            # Check if a scope was provided
            if '::' in v:
                vs = v.split('::')
                pkg_info = lookup_type(view,vs[0])
                v = vs[1]
                if pkg_info and pkg_info['type'] in ['package','class']:
                    if 'fname' in pkg_info:
                        ti = type_info_file(view,pkg_info['fname'][0],v)
                        if ti and 'fname' not in ti:
                            ti['fname'] = pkg_info['fname']
                    # print('Found defintion in package : {}'.format(pkg_info))
            # If in a function body: check for a definition in the function first
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
                # print ('[SV.type_info_on_hier] Looking for type {}'.format(ti))
                ti = lookup_type(view,ti['type'])
                # print ('-> {}'.format(ti))
                if ti and ti['type']:
                    if ti['tag']=='typedef':
                        bti = lookup_type(view,ti['type'])
                        if bti:
                            ti = bti

        # Lookup for the variable inside the type defined
        if not ti:
            return None
        if ti['type']=='struct' :
            if 'fname' in ti:
                loc = ti['fname']
            m = re.search(r'\{(.*)\}', ti['decl'])
            til = verilogutil.get_all_type_info(m.groups()[0])
            ti = None
            for e in til:
                if e['name']==v:
                    ti = e
                    break
        elif 'fname' in ti:
            loc = ti['fname']
            fname = loc[0]
            ti = type_info_file(view,fname,v)
            if ti['type'] in ['function', 'task']:
                with open(fname, 'r', encoding='utf-8') as f:
                    flines = verilogutil.clean_comment(f.read())
                ti = verilogutil.parse_function(flines,v)
        # Propagate the file location
        if ti and loc and 'fname' not in ti :
            ti['fname'] = loc
        # print ('[type_info_on_hier] => type info of {0} = {1}'.format(v,ti))
    return ti

def sort_by_proximity(locs, current_file):
    cur = os.path.normcase(os.path.abspath(current_file))
    cur_dir = os.path.dirname(cur)

    def shared_depth(loc):
        p = os.path.normcase(os.path.abspath(loc.path))  # adapt attr name
        try:
            common = os.path.commonpath([cur_dir, os.path.dirname(p)])
        except ValueError:  # different drives on Windows
            return 0
        return len(common.split(os.sep))

    return sorted(locs, key=shared_depth, reverse=True)

########################################
def lookup_module(view,mname):
    mi = None
    sl = [s for s in view.window().symbol_locations(mname) if s.syntax == 'SystemVerilog' and s.kind[2]=='Type']
    for s in sl:
        fname = sublimeutil.normalize_fname(s.path)
        mi = verilogutil.parse_module_file(fname,mname)
        if mi:
            mi['fname'] = (fname,s.row,s.col)
            break
    # print('[SV:lookup_module] {0}'.format(mi))
    return mi

def lookup_package(view,pkgname):
    pi = None
    mi = None
    # t0 = time.time()
    sl = [s for s in view.window().symbol_locations(pkgname) if s.syntax == 'SystemVerilog' and s.kind[2]=='Type']
    for s in sl:
        mi = None
        if s.path.startswith('<') :
            v = view.window().find_open_file(s.path)
            if v:
                txt = v.substr(sublime.Region(0,v.size()))
                mi = verilogutil.parse_package(txt,pkgname)
        else:
            fname = sublimeutil.normalize_fname(s.path)
            mi = verilogutil.parse_package_file(fname,pkgname)
        if mi:
            pi = {'type': 'package', 'member': mi, 'fname':(fname,s.row,s.col)}
            break
    # print('[SV:lookup_package] Found {} in {}'.format(pkgname, time.time()-t0))
    # print('[SV:lookup_package] {0}'.format(pi))
    return pi

def lookup_function(view,funcname):
    fi = None
    # t0 = time.time()
    sl = [s for s in view.window().symbol_locations(funcname) if s.syntax == 'SystemVerilog' and s.kind[2]=='Function']
    for s in sl:
        fname = sublimeutil.normalize_fname(s.path)
        with open(fname, 'r', encoding='utf-8') as f:
            flines = str(f.read())
        flines = verilogutil.clean_comment(flines)
        fi = verilogutil.parse_function(flines,funcname)
        if fi:
            fi['fname'] = (fname,s.row,s.col)
            break
    # print('[SV:lookup_function] Found {} in {}'.format(funcname, time.time()-t0))
    return fi

def get_import_list(view):
    pkg_fl = []
    txt = verilogutil.clean_comment(view.substr(sublime.Region(0,view.size())))
    for m in re.finditer(r'\bimport\s+(.+?);',txt,flags=re.MULTILINE):
        for mp in re.finditer(r'\b(\w+)(\:\:[\w\*]+)+',m.groups()[0],flags=re.MULTILINE):
            locs_pkg = view.window().symbol_locations(mp.groups()[0], sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)
            pkg_fl += [l.path for l in locs_pkg]
    return pkg_fl

def lookup_type(view, t):
    ti = None
    t0 = time.time()
    pkg_fl = []
    if '::' in t:
        ts = t.split('::')
        locs_pkg = view.window().symbol_locations(ts[0], sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)
        pkg_fl = [l.path for l in locs_pkg]
        # print('[lookup_type] Package {} defined in {}'.format(ts[0],pkg_fl))
        t = ts[-1]

    locs = view.window().symbol_locations(t, sublime.SYMBOL_SOURCE_ANY, sublime.SYMBOL_TYPE_DEFINITION)
    locs_sv = [l for l in locs if l.syntax == 'SystemVerilog']
    locs = sort_by_proximity(locs_sv,  view.buffer().file_name())
    locs_path = [l.path for l in locs]
    # print('locs {}'.format(locs))
    # Get list of impport package if the symbol is defined in more than place and no scope was found
    if len(locs) > 1 and len(pkg_fl)==0:
        pkg_fl = get_import_list(view)
    #
    if len(pkg_fl) > 0:
        pkg_fl = [l for l in pkg_fl if l in locs_path]
    # print('Package list = {} | Current buffer = {}'.format(pkg_fl, view.buffer().file_name()))
    prev_pos = -1
    for loc in locs:
        if len(pkg_fl) > 0 and loc.path in pkg_fl:
            pos = pkg_fl.index(loc.path)
            # Ignore definition which are defined in later package
            if prev_pos > 0 and pos > prev_pos:
                continue
        else :
            pos = -1
        ti = None
        if loc.path.startswith('<') :
            v = view.window().find_open_file(loc.path)
            if v:
                txt = v.substr(sublime.Region(0,v.size()))
                ti = type_info(v,txt,t)
        else:
            ti = type_info_file(view,loc.path,t)
        if ti and ti['type'] and ti['tag']!='typedef' :
            ti['fname'] = (loc.path,loc.row,loc.col)
            prev_pos = pos
            # Stop on first match which when there is no package import or first match inside a package
            if len(pkg_fl) == 0 or pos >= 0:
                break;
    # print('[SV:lookup_type] (pos {}) : {}'.format(prev_pos, ti))
    return ti

def lookup_macro(view, name):
    txt = ''
    params = []
    filelist = view.window().lookup_symbol_in_index(name)
    if filelist:
        fname = view.file_name()
        # Check if symbol is defined in current file first
        if fname in [sublimeutil.normalize_fname(f[0]) for f in filelist]:
            flines = view.substr(sublime.Region(0,view.size()))
            txt,params = verilogutil.get_macro(flines,name)
        else:
            for fi in filelist:
                fname = sublimeutil.normalize_fname(fi[0])
                with open(fname, 'r', encoding='utf-8') as f:
                    flines = str(f.read())
                txt,params = verilogutil.get_macro(flines,name)
                if txt:
                    break
    return txt,params
