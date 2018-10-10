#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from six import BytesIO

from kobo.hub.models import _tail as tail


SAMPLE_LINES = [
    b'this is a sample',
    b'string;     each',
    b'line    contains',
    b'16 chars exclud-',
    b'ing newline, and',
    b'six lines  total'
]
SAMPLE_STRING = b'\n'.join(SAMPLE_LINES)


class TestTail(unittest.TestCase):

    def test_tail_empty(self):
        """tail of empty object returns empty"""
        (actual, offset) = tail(BytesIO(), 1024, 1024)

        self.assertEqual(actual, b'')
        self.assertEqual(offset, 0)

    def test_tail_noop(self):
        """tail returns all content if it fits in requested size"""
        (actual, offset) = tail(BytesIO(SAMPLE_STRING), 1024, 1024)

        self.assertEqual(actual, SAMPLE_STRING)
        self.assertEqual(offset, len(SAMPLE_STRING))

    def test_tail_limit(self):
        """tail returns trailing lines up to given limit"""
        expected = b'\n'.join([
            b'ing newline, and',
            b'six lines  total',
        ])
        (actual, offset) = tail(BytesIO(SAMPLE_STRING), 40, 1024)

        self.assertEqual(actual, expected)
        self.assertEqual(offset, len(SAMPLE_STRING))

    def test_tail_line_break(self):
        """tail breaks in middle of line if lines are longer than max length"""
        expected = b'\n'.join([
            # this line is partially returned
            b'xclud-',
            b'ing newline, and',
            b'six lines  total',
        ])
        (actual, offset) = tail(BytesIO(SAMPLE_STRING), 40, 10)

        self.assertEqual(actual, expected)
        self.assertEqual(offset, len(SAMPLE_STRING))
