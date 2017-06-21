#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Run tests in current directory.
"""

import os
import sys


# prepare environment for tests
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ["PYTHONPATH"] = PROJECT_DIR
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.insert(0, PROJECT_DIR)


from kobo.shortcuts import run


def run_test(test_with_args):
    print "Executing tests in %-40s" % test_with_args[0]
    retcode, output = run(['python'] + test_with_args, can_fail=True)
    if retcode == 0:
        print "[   OK   ]"
        return True
    else:
        print "[ FAILED ]"
        print output
        return False


def run_discovered_tests():
    ok = True
    for test in sorted(os.listdir(os.path.dirname(__file__))):
        # run all tests that match the 'test_*.py" pattern
        if not test.startswith("test_"):
            continue
        if not test.endswith(".py"):
            continue

        if not run_test([test]):
            ok = False

    return ok


if __name__ == '__main__':
    if sys.argv[1:]:
        # arguments passed; assume it's a test, just run it
        ok = run_test(sys.argv[1:])
    else:
        # run all the tests in the directory
        ok = run_discovered_tests()

    sys.exit(0 if ok else 1)
