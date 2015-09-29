import argparse
import pprint
import unittest
import re
import importlib
import os


parser = argparse.ArgumentParser()
parser.add_argument("pattern", nargs='?', default="", help="run tests by name, can be regex")
args = parser.parse_args()

os.chdir(os.path.abspath(os.path.dirname(__file__)))


skipped_tests = ['test_beautifyText10']


test_modules = (os.path.splitext(afile)[0] for afile in os.listdir(".") if afile.endswith("_test.py"))
all_test_classes = (importlib.import_module(i).Tests for i in test_modules)



suite = unittest.TestSuite()
for aclass in all_test_classes:
    for method_name in dir(aclass()):
        if method_name.startswith("test_") and re.search(args.pattern, method_name):
            t = aclass(method_name)
            if method_name in skipped_tests:
                setattr(t, 'setUp', lambda: t.skipTest("not implemented yet"))
            suite.addTest(t)

unittest.TextTestRunner(verbosity=3).run(suite)
