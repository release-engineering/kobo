#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import run_tests # set sys.path

from kobo.types import *


class TestEnum(unittest.TestCase):
    def setUp(self):
        self.enum = Enum(
            "A",
            "B",
            EnumItem("C", help_text="help", foo="foo", bar="bar"),
        )

    def test_in_enum(self):
        self.assert_("A" in self.enum)
        self.assert_("B" in self.enum)
        self.assert_("C" in self.enum)
        self.assert_("X" not in self.enum)

    def test_iter(self):
        self.assertEqual(list(self.enum), ["A", "B", "C"])

    def test_getitem(self):
        self.assertEqual(self.enum["A"], 0)
        self.assertEqual(self.enum["B"], 1)
        self.assertEqual(self.enum["C"], 2)

        self.assertEqual(self.enum[0], "A")
        self.assertEqual(self.enum[1], "B")
        self.assertEqual(self.enum[2], "C")

    def test_get(self):
        self.assertEqual(self.enum.get("B"), 1)
        self.assertEqual(self.enum.get(1), "B")

    def test_get_mapping(self):
        self.assertEqual(self.enum.get_mapping(), [(0, "A"), (1, "B"), (2, "C")])
        self.assertEqual(type(self.enum.get_mapping()[0][1]), str)

    def test_get_item(self):
        self.assertEqual(self.enum.get_item("A"), "A")
        self.assertRaises(KeyError, self.enum.get_item, "X")

    def test_get_help_text(self):
        self.assertEqual(self.enum.get_item_help_text("A"), "")
        self.assertEqual(self.enum.get_item_help_text("C"), "help")

    def test_get_option(self):
        self.assertEqual(self.enum.get_item_option("A", "foo"), None)
        self.assertEqual(self.enum.get_item_option("C", "foo"), "foo")

        self.assertEqual(self.enum.get_item_option("C", "bar"), "bar")
        self.assertEqual(self.enum.get_item_option("C", "bar", "default"), "bar")

        self.assertEqual(self.enum.get_item_option("C", "baz"), None)
        self.assertEqual(self.enum.get_item_option("C", "baz", "default"), "default")

        self.assertEqual(self.enum.get_item("C")["foo"], "foo")
        self.assertRaises(KeyError, self.enum.get_item("C").__getitem__, "baz")


if __name__ == '__main__':
    unittest.main()
