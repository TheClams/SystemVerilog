import os
import re
import argparse
from collections import OrderedDict
import logging

alog = logging.getLogger(__name__)
# TODO: macro func
#    `define                  no macro func
#    `else                    +
#    `elsif                   +
#    `endif                   +
#    `ifdef                   +
#    `ifndef                  +
#    `include                 +
#    `undef                   +
# ignored:
#    `celldefine              -
#    `default_nettype         -
#    `endcelldefine           -
#    `line                    -
#    `nounconnected_drive     -
#    `resetall                -
#    `timescale               -
#    `unconnected_drive       -


class Preprocessor(object):
    def __init__(self, includes=None, defines=None):
        """
            Args:
                includes (list):  Specifies directories to search for files included with `include compiler
                    directives. By default, the current directory is searched first and then the directories
                    specified by the list in the order they appear.

                difines (dict): Allows you to define a macro as {macro_name1: value1, macro_name2: value2}
        """
        self.ignore = {
            '`celldefine',
            '`default_nettype',
            '`endcelldefine',
            '`line',
            '`nounconnected_drive',
            '`resetall',
            '`timescale',
            '`unconnected_drive'
        }

        self.path = "prepr_txt was used"
        self.content = None
        self.unresolved_defines = []
        self.preprocessed = None

        if includes:  # should be a list
            self.includes = [os.getcwd()] + includes
        else:
            self.includes = [os.getcwd()]
        if defines:  # should be a dict
            self.defines = defines
        else:
            self.defines = {}


    def __str__(self):
        aprint = "path: {0.path}\n" \
                 "includes: {0.includes}\n" \
                 "unresolved_defines: {0.unresolved_defines}\n" \
                 "defines: {0.defines}\n".format(self)
        return aprint

    def prepr_file(self, file_in, file_out=None):
        if not file_out:
            file_out = file_in
        self.path = os.path.abspath(file_in)
        self.content = self.read_content(file_in)
        self.prepr_txt()
        with open(file_out, 'w') as f:
            f.write(self.preprocessed)

    def prepr_txt(self, txt=None):
        if txt:
            self.content = txt
        return self.run()

    def run(self):
        # TODO: handle line continuation
        self.content = re.sub(r'\\\n', '', self.content)
        self.content = self.remove_comments(self.content)
        if '`' in self.content:
            self.preprocessed = self.doit(self.content.splitlines())
        else:
            self.preprocessed = self.content

        return self.preprocessed

    def doit(self, content_iter):
        acontent_iter = iter(content_iter)
        result = []
        for line in acontent_iter:
            # delete empty lines
            if line and '`' not in line:
                result.append(line)
            # TODO: one statement per line?
            elif any((i for i in self.ignore if i in line)):
                continue
            elif '`include' in line:
                incl = self.doit(self.prep_include(line))
                result.append(incl)
            elif '`undef' in line:
                self.prep_undef(line)
            elif '`define' in line:
                self.prep_define(line)
            elif '`ifdef' in line or '`ifndef' in line:
                res = self.prep_branch(line, acontent_iter)
                branch = self.doit(res)
                result.append(branch)
            elif line:
                res = self.doit([self.resolve_defines(line)])
                result.append(res)
        return '\n'.join(result)

    def resolve_defines(self, line):
        match = re.search(r'`(\w+)', line)
        macro = match.group()
        resolve = self.defines.get(macro[1:])
        if not resolve:
            resolve = ''
            self.unresolved_defines.append(macro[1:])
            alog.warning('cant resolve ' + line + ' in file ' + self.path)
        return line.replace(macro, resolve)

    def prep_branch(self, aline, acontent_iter):
        blocks = OrderedDict()
        branch = aline
        blocks[branch] = []
        nested = 0
        while True:
            line = next(acontent_iter)
            if '`ifdef' in line or '`ifndef' in line:
                nested += 1
            elif nested and '`endif' in line:
                nested -= 1
                blocks[branch].append(line)
                continue
            if not nested:
                if '`endif' in line:
                    break  # formed branches
                elif {'`elsif', '`else'} & set(line.split()):
                    branch = line
                    blocks[branch] = []
                else:
                    blocks[branch].append(line)
            else:
                blocks[branch].append(line)

        for k, v in blocks.items():
            words = k.split()
            if len(words) >= 2:
                if '`ifndef' in k:
                    if words[1] not in self.defines:
                        return v
                elif words[1] in self.defines:
                    return v
            elif '`else' in k:
                return v
            else:
                alog.warning('Error in macro ' + k)

        return []

    def prep_undef(self, aline):
        words = aline.split()
        if len(words) >= 3 and self.defines.get(words[1]):
            del self.defines[words[1]]

    def prep_define(self, aline):
        words = aline.split()
        qty = len(words)
        if qty >= 3:
            self.defines[words[1]] = ' '.join(words[2:])
        elif qty == 2:
            self.defines[words[1]] = ' '
        else:
            alog.warning('Error in preprocess parsing. Line: ' + aline)

    def iter_flatten(self, iterable):
        it = iter(iterable)
        for e in it:
            if isinstance(e, (list, tuple)):
                for f in self.iter_flatten(e):
                    yield f
            else:
                yield e

    def prep_include(self, aline):
        res = re.search(r'`include\s+"(.+?)"', aline)
        if res:
            incl_file = res.group(1)
            self.includes += [os.path.dirname(self.path)]
            for path in self.includes:
                full_path = os.path.join(path, incl_file)
                if os.path.exists(full_path):
                    incl_content = self.read_content(full_path)
                    return incl_content.splitlines()
        alog.warning('Cannot resolve {} in file: {}'.format(aline,
                                                            os.path.abspath(self.path)))
        return []

    def read_content(self, afile):
        try:
            with open(afile) as f:
                return f.read()
        except IOError:
            raise Exception('Cannot open file: ' + os.path.abspath(self.path))

    # FIXME: code duplication
    def remove_comments(self, acontent):
        def replacer(match):
            s = match.group(0)
            if s.startswith('/'):
                return " "  # note: a space and not an empty string
            else:
                return s
        pattern = re.compile(
            r'//.*?$|/\*.*?\*/|"(?:\\.|[^\\"])*"',
            re.DOTALL | re.MULTILINE
        )
        # do we need trim whitespaces?
        res = re.sub(pattern, replacer, acontent)
        return "\n".join([i.rstrip() for i in res.splitlines()])


if __name__ == '__main__':
    # TODO: vlog style
    # TODO: defines as +define+macro=value+macro2
    # TODO: includes as +incdir+dir_path
    parser = argparse.ArgumentParser(description='Verilog Preprocessor')
    parser.add_argument('-i', '--input',
                        required=True, help='Verilog filename to preprocess')
    parser.add_argument('-o', '--output',
                        required=False, default=None, help='Output filename. Default to input filename.')
    args = parser.parse_args()
    pp = Preprocessor()
    pp.prepr_file(file_in=args.input, file_out=args.output)