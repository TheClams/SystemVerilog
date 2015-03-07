# Class/function to process verilog file
import re, string, os
import pprint

# regular expression for signal/variable declaration:
#   start of line follow by 1 to 4 word,
#   an optionnal array size,
#   an optional list of words
#   the signal itself (not part of the regular expression)
re_var   = r'^\s*(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:\.]*\s+)(\[[\w\:\-\+`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_decl  = r'(?<!@)\s*(?:^|,|\(|;)\s*(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:\.]*\s+)(\[[\w\:\-`\s]+\])?\s*((?:[A-Za-z_]\w*\s*(?:\=\s*\w+)?,\s*)*)\b'
re_enum  = r'^\s*(typedef\s+)?(enum)\s+(\w+\s*)?(\[[\w\:\-`\s]+\])?\s*(\{[\w=,\s`\'\/\*]+\})\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_union = r'^\s*(typedef\s+)?(struct|union)\s+(packed\s+)?(signed|unsigned)?\s*(\{[\w,;\s`\[\:\]\/\*]+\})\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_tdp   = r'^\s*(typedef\s+)(\w+)\s*(#\s*\(.*?\))?\s*()\b'
re_inst  = r'^\s*(virtual)?(\s*)()(\w+)\s*(#\s*\([^;]+\))?\s*()\b'
re_param = r'^\s*parameter\b((?:\s*(?:\w+\s+)?(?:[A-Za-z_]\w+)\s*=\s*(?:[^,;]*)\s*,)*)(\s*(\w+\s+)?([A-Za-z_]\w+)\s*=\s*([^,;]*)\s*;)'

# Port direction list constant
port_dir = ['input', 'output','inout', 'ref']

# TODO: create a class to handle the cache for N module
cache_module = {'mname' : '', 'fname' : '', 'date' : 0, 'info' : None}


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

# Extract the declaration of var_name from txt
#return a tuple: complete string, type, arraytype (none, fixed, dynamic, queue, associative)
def get_type_info(txt,var_name):
    txt = clean_comment(txt)
    m = re.search(re_enum+r'('+var_name+r')\b.*$', txt, flags=re.MULTILINE)
    tag = 'enum'
    idx_type = 1
    idx_bw = 3
    idx_max = 5
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
                m = re.search(re_decl+r'('+var_name+r'\b(\[[^=\^\&\|]*?\]\s*)?)[^\.]*$', txt, flags=re.MULTILINE)
                tag = 'decl'
                idx_type = 3
                idx_bw = 4
                idx_max = 5
                if not m :
                    m = re.search(re_inst+r'('+var_name+r')\b.*$', txt, flags=re.MULTILINE)
                    tag = 'inst'
    # print('[get_type_info] tag = %s , groups = %s' %(tag,str(m.groups())))
    ti = get_type_info_from_match(var_name,m,idx_type,idx_bw,idx_max,tag)[0]
    return ti

# Extract all signal declaration
def get_all_type_info(txt):
    # txt = clean_comment(txt)
    # Cleanup function contents since this can contains some signal declaration
    txt = re.sub(r'(?s)^[ \t\w]*(virtual)?[ \t\w]*(?P<block>function|task)\b.*?\bend(?P=block)\b.*?$','',txt, flags=re.MULTILINE)
    # Suppose text has already been cleaned
    ti = []
    # Look for enum declaration
    # print('Look for enum declaration')
    r = re.compile(re_enum+r'(\w+\b(\s*\[[^=\^\&\|]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,'enum')
        # print('[get_all_type_info] enum groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove enum declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for struct declaration
    # print('Look for struct declaration')
    r = re.compile(re_union+r'(\w+\b(\s*\[[^=\^\&\|]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,'struct')
        # print('[get_all_type_info] struct groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove struct declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for typedef declaration
    # print('Look for typedef declaration')
    r = re.compile(re_tdp+r'(\w+\b(\s*\[[^=\^\&\|]*?\]\s*)?)\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,3,'typedef')
        # print('[get_all_type_info] typedef groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # remove typedef declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look all modports
    r = re.compile(r'modport\s+(\w+)\s+\((.*?)\);', flags=re.MULTILINE)
    modports = r.findall(txt)
    if modports:
        for modport in modports:
            ti.append({'decl':modport[1],'type':'','array':'','bw':'', 'name':modport[0], 'tag':'modport'})
        # print(modports)
        # remove modports before looking for I/O and field to avoid duplication of signals
        txt = r.sub('',txt)
    # Look for signal declaration
    # print('Look for signal declaration')
    r = re.compile(re_decl+r'(\w+\b(\s*\[[^=\^\&\|]*?\]\s*)?)\s*(?=;|,|\)\s*;)',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,3,4,5,'decl')
        # print('[get_all_type_info] decl groups=%s => ti=%s' %(str(m.groups()),str(ti_tmp)))
        ti += [x for x in ti_tmp if x['type']]
    # Look for interface instantiation
    # print('Look for interface instantiation')
    r = re.compile(re_inst+r'(\w+\b(\s*\[[^=\^\&\|]*?\]\s*)?)\s*\(',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,3,4,5,'inst')
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
def get_type_info_from_match(var_name,m,idx_type,idx_bw,idx_max,tag):
    ti_not_found = {'decl':None,'type':None,'array':"",'bw':"", 'name':var_name, 'tag':tag}
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
        elif m.groups()[0] is not None:
            t = str.rstrip(m.groups()[0]) + ' ' + t
    elif t=="const": # identifying a variable as simply const is typical of a struct/union : look for it
        m = re.search( re_union+var_name+r'.*$', txt, flags=re.MULTILINE)
        if m is None:
            return [ti_not_found]
        t = m.groups()[1]
        idx_bw = 3
    # Remove potential false positive
    if t in ['begin','end','else', 'posedge', 'negedge', 'timeunit', 'timeprecision','assign']:
        return [ti_not_found]
    # print("[get_type_info] Group => " + str(m.groups()))
    ft = ''
    bw = ''
    if var_name!='':
        signal_list = re.findall(r'('+var_name + r')\b\s*(\[(.*?)\]\s*)?', m.groups()[idx_max+1], flags=re.MULTILINE)
    else:
        signal_list = []
        if m.groups()[idx_max]:
            signal_list = re.findall(r'(\w+)\b\s*(\[(.*?)\]\s*)?,?', m.groups()[idx_max], flags=re.MULTILINE)
        if m.groups()[idx_max+1]:
            signal_list += re.findall(r'(\w+)\b\s*(\[(.*?)\]\s*)?,?', m.groups()[idx_max+1], flags=re.MULTILINE)
    # remove reserved keyword that could end up in the list
    signal_list = [s for s in signal_list if s[0] not in ['if','case', 'for', 'foreach', 'generate']]
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
            if tmp not in ['end']:
                ft += tmp + ' '
    ti = []
    for signal in signal_list :
        fts = ft + signal[0]
        # print("get_type_info: decl => " + ft)
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
                ma= re.search(r'[A-Za-z_][\w]*',signal[2])
                if ma:
                    at='associative'
                else:
                    at='fixed'
        # print("Array: " + str(m) + "=>" + str(at))
        ti.append({'decl':fts,'type':t,'array':at,'bw':bw, 'name':signal[0], 'tag':tag})
    return ti


# Parse a module for port information
def parse_module_file(fname,mname=r'\w+'):
    # print("Parsing file " + fname + " for module " + mname)
    fdate = os.path.getmtime(fname)
    # Check Cache module
    if cache_module['mname'] == mname and cache_module['fname'] == fname and cache_module['date']==fdate:
        # print('Using cache !')
        return cache_module['info']
    #
    flines = ''
    with open(fname, "r") as f:
        flines = str(f.read())
    flines = clean_comment(flines)
    minfo = parse_module(flines,mname)
    # Put information in cache:
    cache_module['info']  = minfo
    cache_module['mname'] = mname
    cache_module['fname'] = fname
    cache_module['date']  = fdate
    return minfo

def parse_module(flines,mname=r'\w+'):
    # print("Parsing for module " + mname + ' in \n' + flines)
    m = re.search(r"(?s)(?P<type>module|interface)\s+(?P<name>"+mname+")\s*(?P<param>#\s*\(.*?\))?\s*(\((?P<port>.*?)\))?\s*;(?P<content>.*?)(?P<ending>endmodule|endinterface)", flines, re.MULTILINE)
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
    if params:
        for param in params:
            param['value'] = param['value'].strip()
    # Extract all type information inside the module : signal/port declaration, interface/module instantiation
    ati = get_all_type_info(clean_comment(m.group(0)))
    # pprint.pprint(ati,width=200)
    # Extract port name
    ports = []
    ports_name = []
    if m.group('port'):
        s = clean_comment(m.group('port'))
        ports_name = re.findall(r"(\w+)\s*(?=,|$|\[[^=\^\&\|]*?\]\s*(?=,|$))",s)
        # get type for each port
        ports = []
        ports = [ti for ti in ati if ti['name'] in ports_name]
    # Extract instances name
    inst = [ti for ti in ati if ti['type']!='module' and ti['tag']=='inst']
    # Extract signal name
    signals = [ti for ti in ati if ti['type']!='module' and ti['tag']!='inst' and ti['name'] not in ports_name]
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
    ti = []
    # Look for enum declaration
    # print('Look for enum declaration')
    r = re.compile(re_enum+r'(\w+)\b\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,'enum')
        ti += [x for x in ti_tmp if x['type']]
    # Look for struct declaration
    # print('Look for struct declaration')
    r = re.compile(re_union+r'(\w+)\b\s*;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,5,'struct')
        ti += [x for x in ti_tmp if x['type']]
    # remove struct declaration since the content could be interpreted as signal declaration
    txt = r.sub('',txt)
    # Look for typedef of parameterized type
    r = re.compile(re_tdp+r'(\w+)\b\s*;.*$',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,1,3,3,'typedef')
        ti += [x for x in ti_tmp if x['type']]
    # Look for variable declaration
    # print('Look for signal declaration')
    r = re.compile(re_var+r'(\w+(\[[^=\^\&\|]*?\]\s*)?)\b.*?;',flags=re.MULTILINE)
    for m in r.finditer(txt):
        ti_tmp = get_type_info_from_match('',m,3,4,5,'var')
        ti += [x for x in ti_tmp if x['type']]
    return ti

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

