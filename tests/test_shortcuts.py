#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

from kobo.shortcuts import *


class TestEnum(unittest.TestCase):
    def test_force_list(self):
        self.assertEqual(force_list("a"), ["a"])
        self.assertEqual(force_list(["a"]), ["a"])
        self.assertEqual(force_list(["a", "b"]), ["a", "b"])
        
    def test_force_tuple(self):
        self.assertEqual(force_tuple("a"), ("a",))
        self.assertEqual(force_tuple(("a",)), ("a",))
        self.assertEqual(force_tuple(("a", "b")), ("a", "b"))

    def test_allof(self):
        self.assertEqual(allof(), True)
        self.assertEqual(allof(1), True)
        self.assertEqual(allof(True), True)
        self.assertEqual(allof(True, 1, "a"), True)
        self.assertEqual(allof(0), False)
        self.assertEqual(allof(""), False)
        self.assertEqual(allof(None), False)

    def test_anyof(self):
        self.assertEqual(anyof(), False)
        self.assertEqual(anyof(1), True)
        self.assertEqual(anyof(True), True)
        self.assertEqual(anyof(True, 0, "a"), True)
        self.assertEqual(anyof(0), False)
        self.assertEqual(anyof(""), False)
        self.assertEqual(anyof(None), False)

    def test_noneof(self):
        self.assertEqual(noneof(), True)
        self.assertEqual(noneof(False), True)
        self.assertEqual(noneof(True), False)
        self.assertEqual(noneof(False, "", 0), True)
        self.assertEqual(noneof(True, "a", 1), False)
        self.assertEqual(noneof(False, "a", 1), False)
        self.assertEqual(noneof(0, True, False, "a"), False)

    def test_oneof(self):
        self.assertEqual(oneof(), False)
        self.assertEqual(oneof(True), True)
        self.assertEqual(oneof(False), False)
        self.assertEqual(oneof(0, False, "a"), True)
        self.assertEqual(oneof(0, True, False, "a"), False)
        self.assertEqual(oneof(1, True, "a"), False)
        self.assertEqual(oneof(0, False, ""), False)


class TestUtils(unittest.TestCase):
    def test_run(self):
        ret, out = run("echo hello")
        self.assertEqual(ret, 0)
        self.assertEqual(out, "hello\n")
        ret, out = run("exit 1", can_fail=True)
        self.assertEqual(ret, 1)

    def test_parse_checksum_line(self):
        line_text = "d4e64fc7f3c6849888bc456d77e511ca  shortcuts.py"
        checksum, path = parse_checksum_line(line_text)
        self.assertEqual(checksum, "d4e64fc7f3c6849888bc456d77e511ca")
        self.assertEqual(path, "shortcuts.py")
        line_binary = "d4e64fc7f3c6849888bc456d77e511ca *shortcuts.py"
        checksum, path = parse_checksum_line(line_binary)
        self.assertEqual(checksum, "d4e64fc7f3c6849888bc456d77e511ca")
        self.assertEqual(path, "shortcuts.py")


if __name__ == '__main__':
    unittest.main()
