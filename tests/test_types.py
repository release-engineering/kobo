#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest

from kobo.types import Enum, EnumItem, State, StateEnum
from kobo.django.fields import StateEnumField


class TestEnum(unittest.TestCase):
    def setUp(self):
        self.enum = Enum(
            "A",
            "B",
            EnumItem("C", help_text="help", foo="foo", bar="bar"),
        )

    def test_duplicate_items(self):
        self.assertRaises(ValueError, Enum, "A", "A")
        self.assertRaises(ValueError, Enum, EnumItem("A"), "A")

    def test_in_enum(self):
        self.assertTrue("A" in self.enum)
        self.assertTrue("B" in self.enum)
        self.assertTrue("C" in self.enum)
        self.assertTrue("X" not in self.enum)

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


class TestStateEnum(unittest.TestCase):
    def setUp(self):
        def enter_NEW(old_state, new_state, **kwargs):
            if str(new_state) != "NEW":
                raise RuntimeError("new_state == 'NEW' expected.")

        def leave_NEW(old_state, new_state, **kwargs):
            if str(old_state) != "NEW":
                raise RuntimeError("old_state == 'NEW' expected.")

        def enter_CLOSED(old_state, new_state, **kwargs):
            if str(new_state) != "CLOSED":
                raise RuntimeError("new_state == 'CLOSED' expected.")

        self.state_enum = StateEnum(
            State(
                name="NEW",
                next_states=["ASSIGNED", "MODIFIED"],
                enter=[enter_NEW],
                leave=[leave_NEW],
                check_perms=[],
            ),
            State(
                name="ASSIGNED",
                next_states=["MODIFIED"]
            ),
            State(
                name="MODIFIED",
                next_states=["ON_QA"]
            ),
            State(
                name="ON_QA",
                next_states=["VERIFIED", "FAILS_QA"]
            ),
            State(
                name="FAILS_QA",
                next_states=["ASSIGNED", "MODIFIED"]
            ),
            State(
                name="VERIFIED",
                next_states=["CLOSED"]),
            State(
                name="CLOSED",
                next_states=None,
                enter=[enter_CLOSED],
            ),
        )
        self.state_enum.set_state("NEW")

    def test_invalid_states(self):
        self.assertRaises(ValueError, StateEnum,
            State(
                name="NEW",
                next_states=["ASSIGNED", "MODIFIED"],
            ),
            State(
                name="ASSIGNED",
                next_states=["MODIFIED"]
            ),
        )

    def test_transitions(self):
        self.state_enum.set_state("NEW")
        self.state_enum.change_state("MODIFIED")
        self.state_enum.change_state("ON_QA")
        self.state_enum.change_state("VERIFIED")
        self.state_enum.change_state("CLOSED")

        self.state_enum.set_state("NEW")
        # don't commit the state transition -> False
        self.assertEqual(self.state_enum.change_state("MODIFIED", commit=False), False)
        self.assertEqual(self.state_enum.change_state("MODIFIED", commit=True), True)
        # stay in MODIFIED -> False
        self.assertEqual(self.state_enum.change_state("MODIFIED", commit=True), False)

        # and now without the commit argument
        self.state_enum.set_state("NEW")
        self.assertEqual(self.state_enum.change_state("MODIFIED"), True)
        self.assertEqual(self.state_enum.change_state("MODIFIED"), False)

    def test_invalid_transitions(self):
        self.assertRaises(ValueError, self.state_enum.change_state, "CLOSED")
        self.state_enum.change_state("MODIFIED")
        self.assertRaises(ValueError, self.state_enum.change_state, "NEW")
        self.assertRaises(ValueError, self.state_enum.change_state, 0)

    def test_final_states(self):
        self.assertEqual(self.state_enum.get_final_states(), ["CLOSED"])
        self.assertEqual(self.state_enum.get_final_states(return_id_list=True), [6])

    def test_commit(self):
        self.state_enum.set_state('NEW')
        self.assertEqual(self.state_enum._to, None)
        self.state_enum.change_state('MODIFIED', commit=False)
        self.assertEqual(str(self.state_enum), '0')
        self.state_enum.change_state('MODIFIED', commit=True)
        self.assertEqual(str(self.state_enum), '2')
        self.state_enum.change_state('ON_QA', commit=False)
        self.assertEqual(str(self.state_enum), '2')
        self.state_enum.change_state(None, commit=True)
        self.assertEqual(str(self.state_enum), '3')
        # no prepared new_state raises exception
        self.assertRaises(ValueError, self.state_enum.change_state, None, commit=True)


class TestStateEnumField(unittest.TestCase):
    def setUp(self):

        self.state_enum = StateEnum(
            State(
                name="NEW",
                next_states=["ASSIGNED", "MODIFIED"],
                check_perms=[],
            ),
            State(
                name="ASSIGNED",
                next_states=["MODIFIED"]
            ),
            State(
                name="MODIFIED",
                next_states=[]
            ),
        )
        self.state_enum.set_state("NEW")

        self.field = StateEnumField(self.state_enum, default='NEW')

    def test_to_python(self):
        t = self.field.to_python('0')
        self.assertEqual(type(t), StateEnum)
        self.assertEqual(t._current_state, 'NEW')
        t = self.field.to_python('1')
        self.assertEqual(t._current_state, 'ASSIGNED')
        t = self.field.to_python('NEW')
        self.assertEqual(type(t), StateEnum)
        self.assertEqual(t._current_state, 'NEW')
        t = self.field.to_python(t)
        self.assertEqual(type(t), StateEnum)
        self.assertEqual(t._current_state, 'NEW')
        t = self.field.to_python(2)
        self.assertEqual(type(t), StateEnum)
        self.assertEqual(t._current_state, 'MODIFIED')

    def test_choices(self):
        correct = ((0, 'NEW'), (1, 'ASSIGNED'), (2, 'MODIFIED'))
        self.assertEqual(correct, self.field.choices)
