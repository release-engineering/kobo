#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

import tempfile
import os

from kobo.http import POSTTransport


class TestPOSTTransport(unittest.TestCase):
    def setUp(self):
        self.postt = POSTTransport()

    def test_get_content_type(self):
        tf0 = tempfile.mkstemp()[1]
        tf1 = tempfile.mkstemp(suffix=".txt")[1]
        tf2 = tempfile.mkstemp(suffix=".rtf")[1]
        tf3 = tempfile.mkstemp(suffix=".avi")[1]
        self.assertEqual(self.postt.get_content_type(tf0), "application/octet-stream")
        self.assertEqual(self.postt.get_content_type(tf1), "text/plain")
        # *.rtf: py2.7 returns 'application/rtf'; py2.4 returns 'text/rtf'
        self.assertEqual(self.postt.get_content_type(tf2).split("/")[1], "rtf")
        self.assertTrue(self.postt.get_content_type(tf2) in ("application/rtf", "text/rtf"))
        self.assertEqual(self.postt.get_content_type(tf3), "video/x-msvideo")

    def test_add_file(self):
        tf1 = tempfile.mkstemp()[1]
        tf2 = tempfile.mkstemp()[1]
        tf3 = open(tempfile.mkstemp()[1])
        os.unlink(tf1)
        self.assertRaises(OSError, self.postt.add_file, "file", tf1)
        self.assertEqual(self.postt.add_file("file", tf2), None)
        self.assertRaises(TypeError, self.postt.add_file, "file", tf3)
