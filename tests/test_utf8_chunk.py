#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from kobo.hub.models import _utf8_chunk as utf8_chunk

class TestUtf8Chunk(unittest.TestCase):
    def test_noop_ascii(self):
        """utf8_chunk returns input bytes if byte sequence is entirely ASCII"""
        bytestr = b'hello world'
        self.assertIs(utf8_chunk(bytestr), bytestr)

    def test_noop_utf8_end(self):
        """utf8_chunk returns input bytes if byte sequence uses non-ASCII
        UTF-8 at the end of the string and is well-formed"""
        unistr = u'hello 世界'
        bytestr = unistr.encode('utf-8')
        self.assertIs(utf8_chunk(bytestr), bytestr)

    def test_noop_utf8_mid(self):
        """utf8_chunk returns input bytes if byte sequence uses non-ASCII
        UTF-8 in the middle of the string and is well-formed"""
        unistr = u'hello 世界!'
        bytestr = unistr.encode('utf-8')
        self.assertIs(utf8_chunk(bytestr), bytestr)

    def test_noop_invalid(self):
        """utf8_chunk returns input bytes if byte sequence is not valid
        UTF-8 and can't be fixed by truncation"""
        bytestr = b'hello \xff\xff\xff'
        self.assertIs(utf8_chunk(bytestr), bytestr)

    def test_fixup_end(self):
        """utf8_chunk returns copy of input aligned to nearest character boundary
        if input is a byte sequence truncated in the middle of a unicode character."""
        unistr = u'hello 世界'
        bytestr = unistr.encode('utf-8')

        # this is now a broken sequence since we cut it off
        # partway through a character
        bytestr = bytestr[:-1]

        # proving it's broken
        try_decode = lambda: bytestr.decode('utf-8')
        self.assertRaises(UnicodeDecodeError, try_decode)

        # utf8_chunk unbreaks it by removing until the previous
        # complete character
        self.assertEqual(utf8_chunk(bytestr).decode('utf-8'), u'hello 世')
