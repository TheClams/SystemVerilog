import sys
import os
import pprint
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
import verilog_beautifier
class BeautifyConfig():

    def __init__(self, nbSpace=4, useTab=False, oneBindPerLine=True, oneDeclPerLine=False, paramOneLine=True, indentSyle='1tbs', reindentOnly=False, stripEmptyLine=True, instAlignPort=True,ignoreTick=False):
        self.nbSpace        = nbSpace
        self.useTab         = useTab
        self.oneBindPerLine = oneBindPerLine
        self.oneDeclPerLine = oneDeclPerLine
        self.paramOneLine   = paramOneLine
        self.indentSyle     = indentSyle
        self.reindentOnly   = reindentOnly
        self.stripEmptyLine = stripEmptyLine
        self.instAlignPort  = instAlignPort
        self.ignoreTick     = ignoreTick

class Tests(unittest.TestCase):

    path_test = "verilogutil_data/verilog_beautifier/"

    def show_repr(self, actual, expected):
        return "\n\n" \
               "RESULT:\n{raw_actual}\n" \
               "EXPECTED:\n{raw_expected}\n\n".format(raw_actual=actual,raw_expected=expected)

    def runBeautifyTest(self, fname_in, fname_exp, cfg) :
        b = verilog_beautifier.VerilogBeautifier(nbSpace=cfg.nbSpace,
                                                 useTab=cfg.useTab,
                                                 oneBindPerLine=cfg.oneBindPerLine,
                                                 oneDeclPerLine=cfg.oneDeclPerLine,
                                                 paramOneLine=cfg.paramOneLine,
                                                 reindentOnly=cfg.reindentOnly,
                                                 stripEmptyLine=cfg.stripEmptyLine,
                                                 instAlignPort=cfg.instAlignPort,
                                                 ignoreTick=cfg.ignoreTick
                                                 )
        with open(fname_in) as f:
            txt = f.read()
        with open(fname_exp) as f:
            expected = f.read()

        actual = b.beautifyText(txt)
        self.maxDiff = None
        self.assertEqual(actual, expected, msg=self.show_repr(actual, expected))


    def test_beautifyText0(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test0.sv", self.path_test+"test0_expected.sv", cfg)

    def test_beautifyText0Tab(self):
        cfg = BeautifyConfig(useTab=True)
        self.runBeautifyTest(self.path_test+"test0.sv", self.path_test+"test0_tab_expected.sv", cfg)

    def test_beautifyText2(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test2.sv", self.path_test+"test2_expected.sv", cfg)

    def test_beautifyText3(self):
        cfg = BeautifyConfig(nbSpace=3)
        self.runBeautifyTest(self.path_test+"test3.sv", self.path_test+"test3_expected.sv", cfg)

    def test_beautifyText3Indent(self):
        cfg = BeautifyConfig(nbSpace=2, reindentOnly=True, stripEmptyLine=False)
        self.runBeautifyTest(self.path_test+"test3.sv", self.path_test+"test3_indent_expected.sv", cfg)

    def test_beautifyTypedef(self):
        cfg = BeautifyConfig(nbSpace=2)
        self.runBeautifyTest(self.path_test+"typedef.sv", self.path_test+"typedef_exp.sv", cfg)

    def test_beautifyParam(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"param.sv", self.path_test+"param_exp.sv", cfg)

    def test_beautifyText6(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test6.sv", self.path_test+"test6_expected.sv", cfg)

    def test_beautifyText7(self):
        cfg = BeautifyConfig(oneDeclPerLine=True, paramOneLine=False)
        self.runBeautifyTest(self.path_test+"test7.sv", self.path_test+"test7_expected.sv", cfg)

    def test_beautifyModuleDecl(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"module_decl.sv", self.path_test+"module_decl_expected.sv", cfg)

    def test_beautifyModuleImpl(self):
        cfg = BeautifyConfig(nbSpace=3)
        self.runBeautifyTest(self.path_test+"module_import.sv", self.path_test+"module_import_exp.sv", cfg)

    def test_beautifyText9(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test9.sv", self.path_test+"test9_expected.sv", cfg)

    def test_beautifyText10(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test10.sv", self.path_test+"test10_expected.sv", cfg)

    def test_beautifyText11(self):
        cfg = BeautifyConfig(stripEmptyLine=False)
        self.runBeautifyTest(self.path_test+"test11.sv", self.path_test+"test11_expected.sv", cfg)

    def test_beautifyText11Strip(self):
        cfg = BeautifyConfig(stripEmptyLine=True)
        self.runBeautifyTest(self.path_test+"test11.sv", self.path_test+"test11_strip_expected.sv", cfg)

    def test_beautifyText12(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test12.sv", self.path_test+"test12_expected.sv", cfg)

    def test_beautifyText13(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test13.sv", self.path_test+"test13_expected.sv", cfg)

    def test_beautifyText13ign(self):
        cfg = BeautifyConfig(ignoreTick=True)
        self.runBeautifyTest(self.path_test+"test13.sv", self.path_test+"test13_ignore_expected.sv", cfg)

    def test_beautifyPortArray(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"port_array.sv", self.path_test+"port_array_exp.sv", cfg)

    def test_beautifyInstNoAlign(self):
        cfg = BeautifyConfig(instAlignPort=False)
        self.runBeautifyTest(self.path_test+"instance.sv", self.path_test+"instance_no_align.sv", cfg)

    def test_beautifyInst(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"instance_no_align.sv", self.path_test+"instance.sv", cfg)

    def test_beautifyCstyle(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"cstyle_array.sv", self.path_test+"cstyle_array_exp.sv", cfg)

    def test_beautifyAssertion(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"assertion.sv", self.path_test+"assertion_exp.sv", cfg)

    def test_beautifyMacro(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"macro.sv", self.path_test+"macro_exp.sv", cfg)

    def test_extern(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"extern.sv", self.path_test+"extern.sv", cfg)

    def test_always_nobegin(self):
        cfg = BeautifyConfig(nbSpace=3)
        self.runBeautifyTest(self.path_test+"always_nobegin.sv", self.path_test+"always_nobegin_exp.sv", cfg)

    def test_beautifyGenerate(self):
        cfg = BeautifyConfig(nbSpace=3)
        self.runBeautifyTest(self.path_test+"generate.sv", self.path_test+"generate_exp.sv", cfg)

    def test_beautifyModuleParam(self):
        cfg = BeautifyConfig(nbSpace=4)
        self.runBeautifyTest(self.path_test+"module_param.sv", self.path_test+"module_param_exp.sv", cfg)