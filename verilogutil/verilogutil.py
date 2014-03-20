# Class/function to process verilog file
import re, string, os

def clean_comment(txt):
	#remove singleline comment
	txt_nc = re.sub(r"//.*?$","",txt, flags=re.MULTILINE)
	#remove multiline comment
	# txt_nc = re.sub(r"/\*.*\*/","",txt_nc, flags=re.MULTILINE)
	return txt_nc

