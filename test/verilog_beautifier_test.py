import sys
import os
import pprint
import unittest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
import verilog_beautifier
class BeautifyConfig():

    def __init__(self, nbSpace=4, useTab=False, oneBindPerLine=True, oneDeclPerLine=False, paramOneLine=True, indentSyle='1tbs'):
        self.nbSpace        = nbSpace
        self.useTab         = useTab
        self.oneBindPerLine = oneBindPerLine
        self.oneDeclPerLine = oneDeclPerLine
        self.paramOneLine   = paramOneLine
        self.indentSyle     = indentSyle

class Tests(unittest.TestCase):

    path_test = "verilogutil_data/verilog_beautifier/"

    def show_repr(self, actual, expected):
        return "\n\n" \
               "RESULT:\n{raw_actual}\n" \
               "EXPECTED:\n{raw_expected}\n\n" \
               "RESULT REPR:\n{repr_actual}\n" \
               "EXPECTED REPR:\n{repr_expected}" \
               "\n".format(raw_actual=actual,
                           raw_expected=expected,
                           repr_actual=repr(actual),
                           repr_expected=repr(expected))

    def runBeautifyTest(self, fname_in, fname_exp, cfg) :
        b = verilog_beautifier.VerilogBeautifier(nbSpace=cfg.nbSpace,
                                                 useTab=cfg.useTab,
                                                 oneBindPerLine=cfg.oneBindPerLine,
                                                 oneDeclPerLine=cfg.oneDeclPerLine,
                                                 paramOneLine=cfg.paramOneLine)
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

    def test_beautifyText4(self):
        cfg = BeautifyConfig(nbSpace=2)
        self.runBeautifyTest(self.path_test+"test4.sv", self.path_test+"test4_expected.sv", cfg)

    def test_beautifyText5(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test5.sv", self.path_test+"test5_expected.sv", cfg)

    def test_beautifyText6(self):
        cfg = BeautifyConfig()
        self.runBeautifyTest(self.path_test+"test6.sv", self.path_test+"test6_expected.sv", cfg)
