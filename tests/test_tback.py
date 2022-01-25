#!/usr/bin/python
# -*- coding: utf-8 -*-


import re
import six
import unittest

from kobo.tback import get_traceback, Traceback


class TestTraceback(unittest.TestCase):

    def test_empty(self):
        self.assertEqual('', get_traceback())
        self.assertEqual('', Traceback().get_traceback())
        self.assertEqual((None, None, None), Traceback().exc_info)

    def test_text(self):
        try:
            raise Exception('Simple text')
        except:
            str_regexp = re.compile('Traceback \(most recent call last\):\n *File ".*test_tback.py", line .+, in test_text\n *raise Exception\(\'Simple text\'\)\n *Exception: Simple text', re.M)
            bytes_regexp = re.compile(b'Traceback \(most recent call last\):\n *File ".*test_tback.py", line .+, in test_text\n *raise Exception\(\'Simple text\'\)\n *Exception: Simple text', re.M)

            self.assertRegex(get_traceback(), str_regexp)
            tb = Traceback(show_traceback = True, show_code = False, show_locals = False, show_environ = False, show_modules = False)
            self.assertRegex(tb.get_traceback(), bytes_regexp)

    def test_Traceback(self):
        try:
            raise Exception('Simple text')
        except:
            tb = Traceback(show_traceback = False, show_code = False, show_locals = False, show_environ = False, show_modules = False)
        self.assertEqual(b'', tb.get_traceback())
        tb.show_code = True
        self.assertRegex(tb.get_traceback(), re.compile(b'<CODE>.*--> *\d+ *raise Exception.*<\/CODE>$', re.M | re.S))
        tb.show_code = False
        tb.show_locals = True
        self.assertRegex(tb.get_traceback(), re.compile(b'<LOCALS>.*tb = .*<\/LOCALS>$', re.M | re.S))
        tb.show_locals = False
        tb.show_environ = True
        self.assertRegex(tb.get_traceback(), re.compile(b'<ENVIRON>.*<\/ENVIRON>\n<GLOBALS>.*</GLOBALS>$', re.M | re.S))
        tb.show_environ = False
        tb.show_modules = True
        self.assertRegex(tb.get_traceback(), re.compile(b'<MODULES>.*<\/MODULES>$', re.M | re.S))

    def test_encoding(self):
        try:
            a = ''.join([chr(i) for i in range(256)])
            b = u''.join([unichr(i) for i in range(65536)])
            raise Exception()
        except:
            tb = Traceback(show_code = False, show_traceback = False)
        output = tb.get_traceback()
        self.assertIsInstance(output, six.binary_type)

    def test_uninitialized_variables(self):
        class Foo(object):
            __slots__ = ( "bar", "version" )

            def __init__(self):
                self.version = 1

            def test(self):
                try:
                    raise
                except:
                    # bar is uninitialized
                    return Traceback().get_traceback()

        obj = Foo()
        self.assertTrue(obj.test())
