import unittest
import sys
import os

sys.path.insert(1, '../verilogutil')
from vpreprocessor import Preprocessor

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.maxDiff = None
        self.cwd_was = os.getcwd()
        self.data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'verilogutil_data',
                                      'preprocessor')
        os.chdir(self.data_path)

    @classmethod
    def tearDownClass(self):
        os.chdir(self.cwd_was)

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

    def run_test(self, fname_in, fname_exp, cfg=None):
        if cfg:
            p = Preprocessor(includes=cfg.includes, defines=cfg.defines)
        else:
            p = Preprocessor()
        with open(fname_in) as f:
            txt = f.read()
        with open(fname_exp) as f:
            expected = f.read()
        actual = p.prepr_txt(txt)
        self.assertEqual(actual, expected, msg=self.show_repr(actual, expected))

    def test_nested_ifdef(self):
        self.run_test('nested_ifdef.v', 'expected/nested_ifdef.v')

    def test_nested_ifdef2(self):
        self.run_test('nested_ifdef2.v', 'expected/nested_ifdef2.v')

    def test_nested_ifdef3(self):
        self.run_test('nested_ifdef3.v', 'expected/nested_ifdef3.v')

    def test_nested_ifdef4(self):
        self.run_test('nested_ifdef4.v', 'expected/nested_ifdef4.v')

    def test_nested_ifdef5(self):
        self.run_test('nested_ifdef5.v', 'expected/nested_ifdef5.v')

    def test_nested_ifdef6(self):
        self.run_test('nested_ifdef6.v', 'expected/nested_ifdef6.v')

    def test_nested_ifdef7(self):
        self.run_test('nested_ifdef7.v', 'expected/nested_ifdef7.v')

    def test_ifdef(self):
        self.run_test('nested_ifdef.v', 'expected/nested_ifdef.v')

    def test_macro_resolve(self):
        self.run_test('macro_resolve.v', 'expected/macro_resolve.v')

    def test_include(self):
        cfg = Preprocessor(includes=['wrong_path'])
        self.run_test('incl_top.v', 'expected/incl.v', cfg)

    def test_include1(self):
        #cfg = Preprocessor(includes=['wro'])
        self.run_test('incl0', 'expected/incl0')#, cfg)

    def test_removeComments(self):
        self.run_test('comments.v', 'expected/comments.v')

    def test_preprocessor(self):
        self.run_test('dspuva16.v', 'expected/dspuva16.v')



if __name__ == '__main__':
    unittest.main()
