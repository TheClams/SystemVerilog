# Class/function to process verilog file
import re, string, os

# regular expression for signal/variable declaration:
#   start of line follow by 1 to 4 word,
#   an optionnal array size,
#   an optional list of words
#   the signal itself (not part of the regular expression)
re_decl  = r'(?<!@)\s*(?:^|,|\()\s*(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w\:\.]*\s+)(\[[\w\:\-`\s]+\])?\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_enum  = r'^\s*(typedef\s+)?(enum)\s+(\w+\s*)?(\[[\w\:\-`\s]+\])?\s*(\{[\w=,\s`\']+\})\s*([A-Za-z_][\w=,\s]*,\s*)?\b'
re_union = r'^\s*(typedef\s+)?(struct|union)\s+(packed)?(signed|unsigned)?\s*(\{[\w,;\s`\[\:\]]+\})\s*([A-Za-z_][\w=,;\s]*,\s*)?\b'

def clean_comment(txt):
    txt_nc = txt
    #remove multiline comment
    txt_nc = re.sub(r"(?s)/\*.*?\*/","",txt_nc)
    #remove singleline comment
    txt_nc = re.sub(r"//.*?$","",txt_nc, flags=re.MULTILINE)
    return txt_nc

# Extract the declaration of var_name from txt
#return a tuple: complete string, type, arraytype (none, fixed, dynamic, queue, associative)
def get_type_info(txt,var_name):
    txt = clean_comment(txt)
    m = re.search(re_decl+var_name+r'.*$', txt, flags=re.MULTILINE)
    idx_type = 3
    idx_bw = 4
    # print("get_type_info for var " + str(var_name) + " in \n" + str(txt))
    #if regex on signal/variable declaration failed, try looking for an enum, struct or a typedef enum/struct
    if m is None:
        m = re.search(re_enum+var_name+r'.*$', txt, flags=re.MULTILINE)
        if m is None:
            m = re.search(re_union+var_name+r'.*$', txt, flags=re.MULTILINE)
        idx_type = 1
        idx_bw = 3
    #return a tuple of None if not found
    if m is None:
        return {'decl':None,'type':None,'array':"None",'bw':"None", 'name':var_name}
    line = m.group(0).lstrip()
    # print("get_type_info: line=" + line)
    # Extract the type itself: should be the mandatory word, except if is a sign qualifier
    t = str.rstrip(m.groups()[idx_type])
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
            return {'decl':None,'type':None,'array':"None",'bw':"None", 'name':var_name}
        t = m.groups()[1]
        idx_bw = 3
    # print("get_type_info: type => " + str(t))
    ft = ''
    #Concat the first 5 word if not None (basically all signal declaration until signal list)
    for i in range(0,5):
        if m.groups()[i] is not None:
            tmp = str.rstrip(m.groups()[i])
            # Cleanup space in enum/struct declaration
            if i==4 and t in ['enum','struct']:
                tmp = re.sub(r'\s+',' ',tmp,flags=re.MULTILINE)
            # regex can catch more than wanted, so filter based on a list
            if tmp not in ['end']:
                ft += tmp + ' '
    ft += var_name
    # print("get_type_info: decl => " + ft)
    #extract bus width
    bw = str.rstrip(str(m.groups()[idx_bw]))
    # Check if the variable is an array and the type of array (fixed, dynamic, queue, associative)
    at = "None"
    m = re.search(r'\b'+var_name+r'\s*\[([^\]]*)\]', line, flags=re.MULTILINE)
    if m:
        if m.groups()[0] =="":
            at='dynamic'
        elif m.groups()[0]=='$':
            at='queue'
        elif m.groups()[0]=='*':
            at='associative'
        else:
            ma= re.search(r'[A-Za-z_][\w]*',m.groups()[0])
            if ma:
                at='associative'
            else:
                at='fixed'
    # print("Array: " + str(m) + "=>" + str(at))
    return {'decl':ft,'type':t,'array':at,'bw':bw, 'name':var_name}

#
def parse_module(fname):
    flines = ''
    with open(fname, "r") as f:
        flines = str(f.read())
    flines = clean_comment(flines)
    # print(flines)
    m = re.search(r"(?s)module\s+(\w+)\s*(#\s*\([^;]+\))?\s*\((.+?)\)\s*;", flines)
    if m is None:
        print("No module found")
        return None
    mname = m.groups()[0]
    # Extract parameter name
    params = None
    ## Parameter define in ANSI style
    if m.groups()[1] is not None:
        s = clean_comment(m.groups()[1])
        r = re.compile(r"(?P<name>\w+)\s*=\s*(?P<value>[\w\-\+`]+)")
        params = [m.groupdict() for m in r.finditer(s)]
    ##TODO: look for parameter not define in the module declaration (optionnaly?)
    # Extract port name
    ports = None
    if m.groups()[2] is not None:
        s = clean_comment(m.groups()[2])
        ports_name = re.findall(r"(\w+)\s*(?=,|$)",s)
        # get type for each port
        ports = []
        # print("Ports found : " + str(ports_name))
        for p in ports_name:
            ti = get_type_info(flines,str(p))
            # print (ti)
            ports.append(ti)
    return {'name': mname, 'param':params, 'port':ports}
