# Class/function to process verilog file
import re, string, os

# regular expression for signal/variable declaration:
#   start of line follow by 1 to 4 word,
#   an optionnal array size,
#   an optional list of words
#   the signal itself (not part of the regular expression)
re_decl = r'(?:^|,|\()\s*(\w+\s+)?(\w+\s+)?(\w+\s+)?([A-Za-z_][\w:.]*\s+)(\[[\w:-]+\])?\s*([A-Za-z_][\w,]*)?\b'

def clean_comment(txt):
	#remove singleline comment
	txt_nc = re.sub(r"//.*?$","",txt, flags=re.MULTILINE)
	#remove multiline comment
	# txt_nc = re.sub(r"/\*.*\*/","",txt_nc, flags=re.MULTILINE)
	return txt_nc

# Extract the declaration of var_name from txt
#return a tuple: complete string, type, arraytype (none, fixed, dynamic, queue, associative)
def get_type_info(txt,var_name):
    m = re.search(re_decl+var_name, txt)
    # print("get_type_info: " + str(txt))
    #return a tuple of None if not found
    if m is None:
    	return (None,None,None)
    ft = ''
    #Concat the first 5 word if not None (basically all signal declaration until signal list)
    for i in range(0,5):
        if m.groups()[i] is not None:
            ft += str.rstrip(m.groups()[i]) + ' '
    ft += var_name
    # Extract the type itself: should be the mandatory word, except if is a sign qualifier
    t = str.rstrip(m.groups()[3])
    if t=="unsigned" or t=="signed": # TODO check if other cases might happen
        if m.groups()[2] is not None:
            t = str.rstrip(m.groups()[2]) + ' ' + t
        elif m.groups()[1] is not None:
            t = str.rstrip(m.groups()[1]) + ' ' + t
        elif m.groups()[0] is not None:
            t = str.rstrip(m.groups()[0]) + ' ' + t
    # print("Type: " + t)
    # Check if the variable is an array and the type of array (fixed, dynamic, queue, associative)
    at = "None"
    m = re.search(r'\b'+var_name+r'\s*\[([^\]]*)\]', txt)
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
    return (ft,t,at)
