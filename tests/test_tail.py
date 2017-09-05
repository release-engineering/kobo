#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from StringIO import StringIO

from kobo.hub.models import _tail as tail


SAMPLE_LINES = [
    'this is a sample',
    'string;     each',
    'line    contains',
    '16 chars exclud-',
    'ing newline, and',
    'six lines  total'
]
SAMPLE_STRING = '\n'.join(SAMPLE_LINES)


class TestTail(unittest.TestCase):

    def test_tail_empty(self):
        """tail of empty object returns empty"""
        (actual, offset) = tail(StringIO(), 1024, 1024)

        self.assertEqual(actual, '')
        self.assertEqual(offset, 0)

    def test_tail_noop(self):
        """tail returns all content if it fits in requested size"""
        (actual, offset) = tail(StringIO(SAMPLE_STRING), 1024, 1024)

        self.assertEqual(actual, SAMPLE_STRING)
        self.assertEqual(offset, len(SAMPLE_STRING))

    def test_tail_limit(self):
        """tail returns trailing lines up to given limit"""
        expected = '\n'.join([
            'ing newline, and',
            'six lines  total',
        ])
        (actual, offset) = tail(StringIO(SAMPLE_STRING), 40, 1024)

        self.assertEqual(actual, expected)
        self.assertEqual(offset, len(SAMPLE_STRING))

    def test_tail_line_break(self):
        """tail breaks in middle of line if lines are longer than max length"""
        expected = '\n'.join([
            # this line is partially returned
            'xclud-',
            'ing newline, and',
            'six lines  total',
        ])
        (actual, offset) = tail(StringIO(SAMPLE_STRING), 40, 10)

        self.assertEqual(actual, expected)
        self.assertEqual(offset, len(SAMPLE_STRING))


if __name__ == '__main__':
    unittest.main()
