# Class/function to process verilog file
import re, string, os
import pprint
import functools

# regular expression for signal/variable declaration:
#   start of line follow by 1 to 4 word,
#   an optionnal array size,
#   an optional list of words
#   the signal itself (not part of the regular expression)
re_bw    = r'[\w\*\(\)\/><\:\-\+`\$\s]+'
re_var   = r'^\s*(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:\.]*\s+)(\['+re_bw+r'\])?\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_decl  = r'(?<!@)\s*(?:^|,|\(|;)\s*(?:const\s+)?(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:\.]*\s+)(\['+re_bw+r'\])?\s*((?:[A-Za-z_]\w*\s*(?:\=\s*[\w\.\:]+\s*)?,\s*)*)\b'
re_enum  = r'^\s*(typedef\s+)?(enum)\s+(\w+\s*)?(\['+re_bw+r'\])?\s*(\{[\w=,\s`\'\/\*]+\})\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_union = r'^\s*(typedef\s+)?(struct|union|`\w+)\s+(packed\s+)?(signed|unsigned)?\s*(\{[\w,;\s`\[\:\]\/\*]+\})\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_tdp   = r'^\s*(typedef\s+)(\w+)\s*(#\s*\(.*?\))?\s*()\b'
re_inst  = r'^\s*(virtual)?(\s*)()(\w+)\s*(#\s*\([^;]+\))?\s*()\b'
re_param = r'^\s*parameter\b((?:\s*(?:\w+\s+)?(?:[A-Za-z_]\w+)\s*=\s*(?:[^,;]*)\s*,)*)(\s*(\w+\s+)?([A-Za-z_]\w+)\s*=\s*([^,;]*)\s*;)'

# Port direction list constant
port_dir = ['input', 'output','inout', 'ref']


def clean_comment(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    # do we need trim whitespaces?
    return re.sub(pattern, replacer, text)

# Extract declaration of var_name from a file
def get_type_info_file(fname,var_name):
    # print("Parsing file " + fname + " for variable " + var_name)
    fdate = os.path.getmtime(fname)
    ti = get_type_info_file_cache(fname, var_name, fdate)
    # print(get_type_info_file_cache.cache_info())
    return ti

@functools.lru_cache(maxsize=32)
def get_type_info_file_cache(fname, var_name, fdate):
    with open(fname) as f:
        flines = f.read()
        ti = get_type_info(flines, var_name)
    return ti

# Extract the declaration of var_name from txt
#return a tuple: complete string, type, arraytype (none, fixed, dynamic, queue, associative)
def get_type_info(txt,var_name):
    txt = clean_comment(txt)
    m = re.search(re_enum+r'('+var_name+r')\b.*$', txt, flags=re.MULTILINE)
    tag = 'enum'
    idx_type = 1
    idx_bw = 3
    idx_max = 5
    idx_val = -1
    if not m:
        m = re.search(re_union+r'('+var_name+r')\b.*$', txt, flags=re.MULTILINE)
        tag = 'struct'
        if not m:
            idx_type = 1
            idx_bw = 3
            idx_max = 3
            m = re.search(re_tdp+r'('+var_name+r')\b\s*;.*$', txt, flags=re.MULTILINE)
            tag = 'typedef'
            if not m:
                m = re.search(re_decl+r'('+var_name+r'\b(\[[^=\^\&\|,;]*?\]\s*)?)(\s*=\s*([^,;]+))?[^\.]*?$', txt, flags=re.MULTILINE)
                tag = 'decl'
                idx_type = 3
                idx_bw = 4
                idx_max = 5
                idx_val = 9
                if not m :
                    m = re.search(re_inst+r'('+var_name+r')\b.*$', txt, flags=re.MULTILINE)
                    tag = 'inst'
    # print('[get_type_info] tag = %s , groups = %s' %(tag,str(m.groups())))
    ti = get_type_info_from_match(var_name,m,idx_type,idx_bw,idx_max,idx_val,tag)[0]
    return ti

# Extract the macro content from `define name macro_content
def get_macro(txt, name):
    txt = clean_comment(txt)
    m = re.search(r'(?s)^\s*`define\s+'+name+r'\b[ \t]*(?:\((.*?)\)[ \t]*)?(.*?)(?<!\\)\n',txt,re.MULTILINE)
    if not m:
        return ''
    # remove line return
    macro = m.groups()[1].replace('\\\n','')
    param_list = m.groups()[0]
    if param_list:
        param_list = param_list.replace('\\\n','')
    # remove escape character for string
    macro = macro.replace('`"','"')
    # TODO: Expand macro if there is some arguments
    return macro,param_list

# Extract all signal declaration
def get_all_type_info(txt):
    # txt = clean_comment(txt)
    # Cleanup function contents since this can contains some signal declaration
    txt = re.sub(r'(?s)^[ \t\w]*(protected|local)?[ \t\w]*(virtual)?[ \t\w]*(?P<block>function|task)\b.*?\bend(?P=block)\b.*?$','',txt, flags=re.MULTILINE)
    # Cleanup constraint definition
    txt = re.sub(r'(?s)constraint\s+\w+\s*\{\s*([^\{]+?(\s*\{.*?\})?)*?\s*\};','',txt,  flags=re.MULTILINE)
    # Suppose text has already been cleaned
    ti = []
    # Look all modports
    r = re.compile(r'(?s)modport\s+(\w+)\s*\((.*?)\);', flags=re.MULTILINE)
    modports = r.findall(txt)
    if modports:
        for modport in modports:
            ti.append({'decl':modport[1].replace('\n',''),'type':'','array':'','bw':'', 'name':modport[0], 'tag':'modport'})
        # remove modports before looking for I/O and field to avoid duplication of signals
        txt = r.sub('',txt)
    # Look for clocking block
    r = re.compile(r'(?s)clocking\s+(\w+)(.*?)endclocking(\s*:\s*\w+)?', flags=re.MULTILINE)
    cbs = r.findall(txt)
    if cbs:
        for cb in cbs:
            ti.append({'decl':'clocking '+cb[0],'type':'','array':'','bw':'', 'name':cb[0], 'tag':'clocking'})
        # remove clocking block before looking for I/O and field to avoid duplication of signals
        txt = r.sub('',txt)
    # Look for enum declaration
    # print('Look for enum declaration')
    r = re.compile(re_enum+r'(\w+\b(\s*\[[^=\^\&\|,;]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,-1,'enum')
        # print('[get_all_type_info] enum groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove enum declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for struct declaration
    # print('Look for struct declaration')
    r = re.compile(re_union+r'(\w+\b(\s*\[[^=\^\&\|,;]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,-1,'struct')
        # print('[get_all_type_info] struct groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove struct declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for typedef declaration
    # print('Look for typedef declaration')
    r = re.compile(re_tdp+r'(\w+\b(\s*\[[^=\^\&\|,;]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,3,-1,'typedef')
        # print('[get_all_type_info] typedef groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove typedef declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for signal declaration
    # print('Look for signal declaration')
    # TODO: handle init value
    re_str = re_decl+r'(\w+\b(\s*\[[^=\^\&\|,;]*?\]\s*)?)\s*(?:\=\s*[\w\.\:]+\s*)?(?=;|,|\)\s*;)'
    r = re.compile(re_str,flags=re.MULTILINE)
    # print('[get_all_type_info] decl re="{0}'.format(re_str))
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,3,4,5,-1,'decl')
        # print('[get_all_type_info] decl groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # Look for interface instantiation
    # print('Look for interface instantiation')
    r = re.compile(re_inst+r'(\w+\b(\s*\[[^=\^\&\|,;]*?\]\s*)?)\s*\(',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,3,4,5,-1,'inst')
        # print('[get_all_type_info] inst groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # print(ti)
    # Look for non-ansi declaration where a signal is declared twice (I/O then reg/wire) and merge it into one declaration
    ti_dict = {}
    pop_list = []
    for (i,x) in enumerate(ti[:]) :
        if x['name'] in ti_dict:
            ti_index = ti_dict[x['name']][1]
            # print('[get_all_type_info] Duplicate found for %s => %s and %s' %(x['name'],ti_dict[x['name']],x))
            if ti[ti_index]['type'].split()[0] in ['input', 'output', 'inout']:
                ti[ti_index]['decl'] = ti[ti_index]['decl'].replace(ti[ti_index]['type'],ti[ti_index]['type'].split()[0] + ' ' + x['type'])
                ti[ti_index]['type'] = x['type']
                pop_list.append(i)
        else :
            ti_dict[x['name']] = (x,i)
    for i in sorted(pop_list,reverse=True):
        ti.pop(i)
    # pprint.pprint(ti, width=200)
    return ti

# Get type info from a match object
def get_type_info_from_match(var_name,m,idx_type,idx_bw,idx_max,idx_val,tag):
    ti_not_found = {'decl':None,'type':None,'array':"",'bw':"", 'name':var_name, 'tag':tag, 'value':None}
    #return a tuple of None if not found
    if not m:
        return [ti_not_found]
    if not m.groups()[idx_type]:
        return [ti_not_found]
    line = m.group(0).strip()
    # Extract the type itself: should be the mandatory word, except if is a sign qualifier
    t = str.rstrip(m.groups()[idx_type]).split('.')[0]
    if t=="unsigned" or t=="signed": # TODO check if other cases might happen
        if m.groups()[2] is not None:
            t = str.rstrip(m.groups()[2]) + ' ' + t
        elif m.groups()[1] is not None:
            t = str.rstrip(m.groups()[1]) + ' ' + t
        elif m.groups()[0] is not None and not m.groups()[0].startswith('end'):
            t = str.rstrip(m.groups()[0]) + ' ' + t
    elif t=="const": # identifying a variable as simply const is typical of a struct/union : look for it
        m = re.search( re_union+var_name+r'.*$', txt, flags=re.MULTILINE)
        if m is None:
            return [ti_not_found]
        t = m.groups()[1]
        idx_bw = 3
    # Remove potential false positive
    if t in ['begin', 'end', 'endspecify', 'else', 'posedge', 'negedge', 'timeunit', 'timeprecision','assign', 'disable', 'property', 'initial']:
        return [ti_not_found]
    # print("[get_type_info] Group => " + str(m.groups()))
    value = None
    ft = ''
    bw = ''
    if var_name!='':
        signal_list = re.findall(r'('+var_name + r')\b\s*(\[(.*?)\]\s*)?', m.groups()[idx_max+1], flags=re.MULTILINE)
        if idx_val > 0 and len(m.groups())>idx_val and m.groups()[idx_val]:
            value = str.rstrip(m.groups()[idx_val])
    else:
        signal_list = []
        if m.groups()[idx_max]:
            signal_list = re.findall(r'(\w+)\b\s*(\[(.*?)\]\s*)?,?', m.groups()[idx_max], flags=re.MULTILINE)
        if m.groups()[idx_max+1]:
            signal_list += re.findall(r'(\w+)\b\s*(\[(.*?)\]\s*)?,?', m.groups()[idx_max+1], flags=re.MULTILINE)
    # remove reserved keyword that could end up in the list
    signal_list = [s for s in signal_list if s[0] not in ['if','case', 'for', 'foreach', 'generate', 'input', 'output', 'inout']]
    # print("[get_type_info] signal_list = " + str(signal_list) + ' for line ' + line)
    #Concat the first 5 word if not None (basically all signal declaration until signal list)
    for i in range(0,idx_max):
        # print('[get_type_info_from_match] tag='+tag+ ' name='+str(signal_list)+ ' match (' + str(i) + ') = ' + str(m.groups()[i]).strip())
        if m.groups()[i] is not None:
            tmp = m.groups()[i].strip()
            # Cleanup space in enum/struct declaration
            if i==4 and t in ['enum','struct']:
                tmp = re.sub(r'\s+',' ',tmp,flags=re.MULTILINE)
            #Cleanup spaces in bitwidth
            if i==idx_bw:
                tmp = re.sub(r'\s+','',tmp,flags=re.MULTILINE)
                bw = tmp
            # regex can catch more than wanted, so filter based on a list
            if not tmp.startswith('end'):
                ft += tmp + ' '
    if not ft.strip():
        return [ti_not_found]
    ti = []
    for signal in signal_list :
        fts = ft + signal[0]
        # Check if the variable is an array and the type of array (fixed, dynamic, queue, associative)
        at = ""
        if signal[1]!='':
            fts += '[' + signal[2] + ']'
            if signal[2] =="":
                at='dynamic'
            elif signal[2]=='$':
                at='queue'
            elif signal[2]=='*':
                at='associative'
            else:
                ma= re.match(r'[A-Za-z_][\w]*$',signal[2])
                if ma:
                    at='associative'
                else:
                    at='fixed'
        d = {'decl':fts,'type':t,'array':at,'bw':bw, 'name':signal[0], 'tag':tag, 'value': value}
        ft0 = ft.split()[0]
        if ft0 in ['local','protected']:
            d['access'] = ft0
        # TODO: handle init value inside list
        # print("Array: " + str(m) + "=>" + str(at))
        ti.append(d)
    return ti


# Parse a module for port information
def parse_module_file(fname,mname=r'\w+'):
    # print("Parsing file " + fname + " for module " + mname)
    fdate = os.path.getmtime(fname)
    minfo = parse_module_file_cache(fname, mname, fdate)
    # print(parse_module_file_cache.cache_info())
    return minfo

@functools.lru_cache(maxsize=32)
def parse_module_file_cache(fname, mname, fdate):
    with open(fname) as f:
        flines = f.read()
        minfo = parse_module(flines, mname)
    return minfo

def parse_module(flines,mname=r'\w+'):
    # print("Parsing for module " + mname + ' in \n' + flines)
    flines = clean_comment(flines)
    m = re.search(r"(?s)(?P<type>module|interface)\s+(?P<name>"+mname+r")(?P<import>\s+import\s+.*?;)?\s*(#\s*\((?P<param>.*?)\))?\s*(\((?P<port>.*?)\))?\s*;(?P<content>.*?)(?P<ending>endmodule|endinterface)", flines, re.MULTILINE)
    if m is None:
        return None
    mname = m.group('name')
    # Extract parameter name
    params = []
    param_type = ''
    ## Parameter define in ANSI style
    r = re.compile(r"(parameter\s+)?(?P<decl>\b\w+\b\s*(\[[\w\:\-\+`\s]+\]\s*)?)?(?P<name>\w+)\s*=\s*(?P<value>[^,;\n]+)")
    if m.group('param'):
        s = clean_comment(m.group('param'))
        for mp in r.finditer(s):
            params.append(mp.groupdict())
            if not params[-1]['decl']:
                params[-1]['decl'] = param_type;
            else :
                params[-1]['decl'] = params[-1]['decl'].strip();
                param_type = params[-1]['decl']
    ## look for parameter not define in the module declaration
    if m.group('content'):
        s = clean_comment(m.group('content'))
        r_param_list = re.compile(re_param,flags=re.MULTILINE)
        for mpl in r_param_list.finditer(s):
            param_type = ''
            for mp in r.finditer(mpl.group(0)):
                params.append(mp.groupdict())
                if not params[-1]['decl']:
                    params[-1]['decl'] = param_type;
                else :
                    params[-1]['decl'] = params[-1]['decl'].strip();
                    param_type = params[-1]['decl']
    ## Cleanup param value
    params_name = []
    if params:
        for param in params:
            param['value'] = param['value'].strip()
            params_name.append(param['name'])
    # Extract all type information inside the module : signal/port declaration, interface/module instantiation
    ati = get_all_type_info(clean_comment(m.group(0)))
    # pprint.pprint(ati,width=200)
    # Extract port name
    ports = []
    ports_name = []
    if m.group('port'):
        s = clean_comment(m.group('port'))
        ports_name = re.findall(r"(\w+)\s*(?=,|$|\[[^=\^\&\|,;]*?\]\s*(?=,|$))",s)
        # get type for each port
        ports = []
        ports = [ti for ti in ati if ti['name'] in ports_name]
    ports_name += params_name
    # Extract instances name
    inst = [ti for ti in ati if ti['type']!='module' and ti['type']!='interface' and ti['tag']=='inst']
    # Extract signal name
    signals = [ti for ti in ati if ti['type'] not in ['module','interface','modport'] and ti['tag']!='inst' and ti['name'] not in ports_name ]
    minfo = {'name': mname, 'param':params, 'port':ports, 'inst':inst, 'type':m.group('type'), 'signal' : signals}
    modports = [ti for ti in ati if ti['tag']=='modport']
    if modports:
        minfo['modport'] = modports
    # pprint.pprint(minfo,width=200)
    return minfo

def parse_package(flines,pname=r'\w+'):
    # print("Parsing for module " + pname + ' in \n' + flines)
    m = re.search(r"(?s)(?P<type>package)\s+(?P<name>"+pname+")\s*;\s*(?P<content>.+?)(?P<ending>endpackage)", flines, re.MULTILINE)
    if m is None:
        return None
    txt = clean_comment(m.group('content'))
    ti = get_all_type_info(txt)
    # print(ti)
    return ti

def parse_function(flines,funcname):
    m = re.search(r'(?s)(\b(protected|local)\s+)?(\bvirtual\s+)?\b((function|task)\s+(\w+\s+)?(\w+\s+|\[[\d:]+\]\s+)?)\b(' + funcname + r')\b\s*(\((.*?)\s*\))?\s*;(.*?)\bend\5\b',flines,re.MULTILINE)
    if not m:
        return None
    if m.groups()[9]:
        ti = get_all_type_info(m.groups()[9] + ';')
    else:
        ti_all = get_all_type_info(m.groups()[10])
        ti = [x for x in ti_all if x['decl'].startswith(('input','output','inout'))]
    fi = {'name': funcname,'type': m.groups()[4],'decl': m.groups()[3] + ' ' + funcname, 'port' : ti}
    if m.groups()[1]:
        fi['access'] = m.groups()[1]
    return fi

# Parse a class for function and members
def parse_class_file(fname,cname=r'\w+'):
    # print("Parsing file " + fname + " for module " + mname)
    fdate = os.path.getmtime(fname)
    info = parse_class_file_cache(fname, cname, fdate)
    # print(parse_class_file_cache.cache_info())
    return info

@functools.lru_cache(maxsize=32)
def parse_class_file_cache(fname, cname, fdate):
    with open(fname) as f:
        contents = f.read()
        flines = clean_comment(contents)
        info = parse_class(flines, cname)
    return info

def parse_class(flines,cname=r'\w+'):
    # print("Parsing for class " + cname + ' in \n' + flines)
    m = re.search(r"(?s)(?P<type>class)\s+(?P<name>"+cname+")\s*(#\s*\((?P<param>.*?)\))?\s*(extends\s+(?P<extend>\w+(?:\s*#\(.*?\))?))?\s*;(?P<content>.*?)(?P<ending>endclass)", flines, re.MULTILINE)
    if m is None:
        return None
    txt = clean_comment(m.group('content'))
    ci = {'type':'class', 'name': m.group('name'), 'extend': None if 'extend' not in m.groupdict() else m.group('extend'), 'function' : []}
    # TODO: handle parameters ...
    # Extract all functions
    fl = re.findall(r'(?s)(\b(protected|local)\s+)?(\bvirtual\s+)?\b(function|task)\s+((?:\w+\s+)?(?:\w+\s+)?)\b(\w+)\b\s*\((.*?)\s*\)\s*;',flines,re.MULTILINE)
    for (_,f_access, f_virtual, f_type, f_return,f_name,f_args) in fl:
        d = {'name': f_name, 'type': f_type, 'args': f_args, 'return': f_return}
        if f_access:
            d['access'] = f_access
        ci['function'].append(d)
    # Extract members
    ci['member'] = get_all_type_info(txt)
    # print(ci)
    return ci

# Fill all entry of a case for enum or vector (limited to 8b)
# ti is the type infor return by get_type_info
def fill_case(ti,length=0):
    if not ti['type']:
        print('[fill_case] No type for signal ' + str(ti['name']))
        return (None,None)
    t = ti['type'].split()[0]
    s = '\n'
    if t == 'enum':
        # extract enum from the declaration
        m = re.search(r'\{(.*)\}', ti['decl'])
        if m :
            el = re.findall(r"(\w+).*?(,|$)",m.groups()[0])
            maxlen = max([len(x[0]) for x in el])
            if maxlen < 7:
                maxlen = 7
            for x in el:
                s += '\t' + x[0].ljust(maxlen) + ' : ;\n'
            s += '\tdefault'.ljust(maxlen+1) + ' : ;\nendcase'
            return (s,[x[0] for x in el])
    elif t in ['logic','bit','reg','wire','input','output']:
        m = re.search(r'\[\s*(\d+)\s*\:\s*(\d+)',ti['bw'])
        if m :
            # If no length was provided use the complete bitwidth
            if length>0:
                bw = length
            else :
                bw = int(m.groups()[0]) + 1 - int(m.groups()[1])
            if bw <=8 :
                for i in range(0,(1<<bw)):
                    s += '\t' + str(i).ljust(7) + ' : ;\n'
                s += '\tdefault : ;\nendcase'
                return (s,range(0,(1<<bw)))
    print('[fill_case] Type not supported: ' + str(t))
    return (None,None)

