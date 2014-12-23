import sys
import os
import pprint
import unittest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
from verilogutil import parse_module, clean_comment

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _helper(self, data_dir):
        for root, _, files in os.walk(data_dir):
            for afile in files:
                aname, atype = os.path.splitext(afile)
                if atype == '.sv':
                    test_file = os.path.join(root, afile)
                    expected_file = os.path.join(root, aname + '.yaml')
                    yield test_file, expected_file

    def test_clean_comment(self):
        data_path = os.path.join('verilogutil_data', 'clean_comment_data')
        for test_file, expected_file in self._helper(data_path):
            with open(test_file) as af, open(expected_file) as ef:
                actual = clean_comment(af.read())
                actual = "\n".join((i.strip() for i in actual.splitlines()))
                # print(repr(actual))
                expected = ef.read()
                self.assertEqual(actual, expected, msg="See test: "+str(test_file))

    def test_parse_module(self):
        data_path = os.path.join('verilogutil_data', 'parse_module_data')
        for test_file, expected_file in self._helper(data_path):
            with open(test_file) as af, open(expected_file) as ef:
                actual = parse_module(af.read())
                # pprint.pprint(actual)
                # print(yaml.dump(actual, default_flow_style=False))
                expected = yaml.load(ef)
                self.assertEqual(actual, expected, msg="See test: "+str(test_file))


def run_tests():
    tests = [
        'test_parse_module',
        'test_clean_comment',
    ]

    suite = unittest.TestSuite(list(map(Tests, tests)))
    unittest.TextTestRunner(verbosity=3).run(suite)

if __name__ == '__main__':
    unittest.main()
    # run_tests()