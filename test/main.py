import argparse
import pprint
import unittest
import re
import verilogutil_test


# import sys
# sys.argv.append("-n=comment")
parser = argparse.ArgumentParser()
parser.add_argument("pattern", help="run tests by name, can be regex")
args = parser.parse_args()


all_test_classes = (verilogutil_test.Tests,)
suite = unittest.TestSuite()
for cl in all_test_classes:
    filtered_tests = [cl(i) for i in dir(cl()) if i.startswith("test_") and re.search(args.pattern, i)]
    suite.addTests(filtered_tests)
unittest.TextTestRunner(verbosity=3).run(suite)



