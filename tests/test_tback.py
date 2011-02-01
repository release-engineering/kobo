#!/usr/bin/python
# -*- coding: utf-8 -*-


import re
import unittest
import run_tests # set sys.path

from kobo.tback import *


class TestTraceback(unittest.TestCase):
    def test_empty(self):
        self.assertEqual('', get_traceback())
        self.assertEqual('', Traceback().get_traceback())
        self.assertEqual((None, None, None), Traceback().exc_info)

    def test_text(self):
        try:
            raise Exception('Simple text')
        except:
            regexp = re.compile('Traceback \(most recent call last\):\n *File ".*test_tback.py", line .+, in test_text\n *raise Exception\(\'Simple text\'\)\n *Exception: Simple text', re.M)
            self.assertRegexpMatches(get_traceback(), regexp)
            tb = Traceback(show_traceback = True, show_code = False, show_locals = False, show_environ = False, show_modules = False)
            self.assertRegexpMatches(tb.get_traceback(), regexp)

    def test_Traceback(self):
        try:
            raise Exception('Simple text')
        except:
            tb = Traceback(show_traceback = False, show_code = False, show_locals = False, show_environ = False, show_modules = False)
        self.assertEqual('', tb.get_traceback())
        tb.show_code = True
        self.assertRegexpMatches(tb.get_traceback(), re.compile('<CODE>.*--> *\d+ *raise Exception.*<\/CODE>$', re.M | re.S))
        tb.show_code = False
        tb.show_locals = True
        self.assertRegexpMatches(tb.get_traceback(), re.compile('<LOCALS>.*tb = .*<\/LOCALS>$', re.M | re.S))
        tb.show_locals = False
        tb.show_environ = True
        self.assertRegexpMatches(tb.get_traceback(), re.compile('<ENVIRON>.*<\/ENVIRON>\n<GLOBALS>.*</GLOBALS>$', re.M | re.S))
        tb.show_environ = False
        tb.show_modules = True
        self.assertRegexpMatches(tb.get_traceback(), re.compile('<MODULES>.*<\/MODULES>$', re.M | re.S))

    def test_encoding(self):
        try:
            a = ''.join([chr(i) for i in range(256)])
            b = u''.join([unichr(i) for i in range(65536)])
            raise Exception()
        except:
            tb = Traceback(show_code = False, show_traceback = False)
        output = tb.get_traceback()
        self.assertIsInstance(output, str)


if __name__ == "__main__":
    unittest.main()
