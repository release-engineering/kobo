#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

from kobo.conf import *


CONFIG = """
integer1 = 1
integer2 = -1

float1 = 1.0
float2 = -1.0

boolean1 = True
boolean2 = False

dict = {"a": 1, "b": True, "c": None, True: False, "tuple": (1, "a"), "list": [1, "a"]}

tuple1 = ()
tuple2 = (1, )
tuple3 = (1, "a")

list1 = []
list2 = [1, ]
list3 = [1, "a"]

string1 = "a string"
string2 = "This is %s." % string1
string3 = "int: %d" % 1
string4 = "float: %f" % 1.0
string5 = "%(a)d %(b)s" % dict
"""


class TestConf(unittest.TestCase):
    def setUp(self):
        self.conf = PyConfigParser()
        self.conf.load_from_string(CONFIG)

    def test_integer(self):
        self.assertEqual(self.conf["integer1"], 1)
        self.assertEqual(self.conf["integer2"], -1)

    def test_float(self):
        self.assertEqual(self.conf["float1"], 1.0)
        self.assertEqual(self.conf["float2"], -1.0)

    def test_boolean(self):
        self.assertEqual(self.conf["boolean1"], True)
        self.assertEqual(self.conf["boolean2"], False)

    def test_string(self):
        self.assertEqual(self.conf["string1"], "a string")
        self.assertEqual(self.conf["string2"], "This is a string.")
        self.assertEqual(self.conf["string3"], "int: 1")
        self.assertEqual(self.conf["string4"], "float: 1.000000")
        self.assertEqual(self.conf["string5"], "1 True")

    def test_dict(self):
        self.assertEqual(self.conf["dict"], {"a": 1, "b": True, "c": None, True: False, "tuple": (1, "a"), "list": [1, "a"]})

    def test_tuple(self):
        self.assertEqual(self.conf["tuple1"], ())
        self.assertEqual(self.conf["tuple2"], (1, ))
        self.assertEqual(self.conf["tuple3"], (1, "a"))

    def test_list(self):
        self.assertEqual(self.conf["list1"], [])
        self.assertEqual(self.conf["list2"], [1])
        self.assertEqual(self.conf["list3"], [1, "a"])


if __name__ == '__main__':
    unittest.main()
