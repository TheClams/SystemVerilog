import sys
import os
import pprint
import unittest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
import verilog_beautifier

class Tests(unittest.TestCase):

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


    def test_beautifyText0(self):
        b = verilog_beautifier.VerilogBeautifier(nbSpace=4,
                                                 useTab=False,
                                                 oneBindPerLine=True,
                                                 oneDeclPerLine=False,
                                                 paramOneLine=False)
        print(os.getcwd())
        with open("verilogutil_data/verilog_beautifier/test0.sv") as f:
            txt = f.read()
        with open("verilogutil_data/verilog_beautifier/test0_expected.sv") as f:
            expected = f.read()

        actual = b.beautifyText(txt)
        self.assertEqual(actual, expected, msg=self.show_repr(actual, expected))

    def test_beautifyText1(self):
        b = verilog_beautifier.VerilogBeautifier(nbSpace=4,
                                                 useTab=True,
                                                 oneBindPerLine=True,
                                                 oneDeclPerLine=False,
                                                 paramOneLine=False)
        print(os.getcwd())
        with open("verilogutil_data/verilog_beautifier/test1.sv") as f:
            txt = f.read()
        with open("verilogutil_data/verilog_beautifier/test1_expected.sv") as f:
            expected = f.read()

        actual = b.beautifyText(txt)
        self.assertEqual(actual, expected, msg=self.show_repr(actual, expected))

    def test_beautifyText2(self):
        b = verilog_beautifier.VerilogBeautifier(nbSpace=4,
                                                 useTab=False,
                                                 oneBindPerLine=True,
                                                 oneDeclPerLine=False,
                                                 paramOneLine=False)
        print(os.getcwd())
        with open("verilogutil_data/verilog_beautifier/test2.sv") as f:
            txt = f.read()
        with open("verilogutil_data/verilog_beautifier/test2_expected.sv") as f:
            expected = f.read()

        actual = b.beautifyText(txt)
        self.assertEqual(actual, expected, msg=self.show_repr(actual, expected))

