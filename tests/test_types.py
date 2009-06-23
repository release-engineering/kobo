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
            "C",
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


if __name__ == '__main__':
    unittest.main()
