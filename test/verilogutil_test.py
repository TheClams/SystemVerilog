import sys
import os
import pprint
import unittest
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
from verilogutil import parse_module, parse_package, clean_comment


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def setUp(self):
        pass

    def tearDown(self):
        pass


def _clean_comment(test_file, expected_file):
    def test(self):
        with open(test_file) as af, open(expected_file) as ef:
            actual = clean_comment(af.read())
            actual = "\n".join((i.strip() for i in actual.splitlines()))
            # print(repr(actual))
            expected = ef.read()
            self.assertEqual(actual, expected, msg="See test: "+str(test_file))
    return test


def _parse_module(test_file, expected_file):
    def test(self):
        with open(test_file) as af, open(expected_file) as ef:
            actual = parse_module(af.read())
            # print(json.dumps(actual, indent=4))
            expected = json.load(ef)
            self.assertEqual(actual, expected, msg="See test: "+str(test_file))
    return test


def _parse_package(test_file, expected_file):
    def test(self):
        with open(test_file) as af, open(expected_file) as ef:
            actual = parse_package(af.read())
            # print(json.dumps(actual, indent=4))
            expected = json.load(ef)
            self.assertEqual(actual, expected, msg="See test: "+str(test_file))
    return test


def _helper(data_dir):
    for root, _, files in os.walk(data_dir):
        for afile in files:
            aname, atype = os.path.splitext(afile)
            if atype == '.sv':
                test_file = os.path.join(root, afile)
                expected_file = os.path.join(root, aname + '.json')
                yield aname, test_file, expected_file


def bind_test_suite(method, data_path):
    for test_id, test_file_path, expected_file_path in _helper(data_path):
        test = method(test_file_path, expected_file_path)
        test_name = "test{}_{}".format(method.__name__, test_id)
        setattr(Tests, test_name, test)


def bind_all_tests():
    suites = (
        (_parse_module, os.path.join('verilogutil_data', 'parse_module_data')),
        (_parse_package, os.path.join('verilogutil_data', 'parse_package')),
        (_clean_comment, os.path.join('verilogutil_data', 'clean_comment_data'))
    )
    for method, data_path in suites:
        bind_test_suite(method, data_path)

# dynamically populate class Tests with test methods
bind_all_tests()


def run_specific_test(t="test_clean_comment_test0"):
    suite = unittest.TestSuite()
    suite.addTest(Tests(t))
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    unittest.main()
    # run_specific_test("test_parse_module_test3")
    # to run one test execute
    # py -m unittest verilogutil_test.Tests.test_clean_comment_test0