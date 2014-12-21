import sys
import os
import pprint
import unittest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'verilogutil'))
from verilogutil import parse_module

class Tests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse_module(self):
        self.maxDiff = None
        for root, _, files in os.walk(os.path.join('verilogutil_data', 'parse_module_data')):
            # files = ["test1.sv"]
            for afile in files:
                aname, atype = os.path.splitext(afile)
                if atype:  # ignore files without extension
                    test_file = os.path.join(root, afile)
                    expected_file = os.path.join(root, aname)
                    with open(test_file) as af:
                        actual = parse_module(af.read())
                        # pprint.pprint(actual)
                        # print(yaml.dump(actual, default_flow_style=False))
                        with open(expected_file) as ef:
                            expected = yaml.load(ef)
                            self.assertEqual(actual, expected, msg="See test: "+str(test_file))


def runTests():
    tests = [
        'test_parse_module'
    ]

    suite = unittest.TestSuite(list(map(Tests, tests)))
    unittest.TextTestRunner(verbosity=3).run(suite)

if __name__ == '__main__':
    unittest.main()
    # runTests()