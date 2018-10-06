#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

import tempfile
import os.path
import shutil

from kobo.hardlink import Hardlink, UndoHardlink


class LoggerMock(object):
    def __init__(self):
        self.loglvl = None
        self.msg = None

    def log(self, loglvl, msg):
        self.loglvl = loglvl
        self.msg = msg


class TestHardlinkClass(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_link(self):
        path_src = os.path.join(self.tmp_dir, "a")
        open(path_src, 'w').write("asdf")
        path_dst = os.path.join(self.tmp_dir, "b")

        hl = Hardlink()
        hl.link(path_src, path_dst)

        self.assertEqual(os.stat(path_src),  os.stat(path_dst))

    def test_log(self):
        logger = LoggerMock()
        hl = Hardlink(logger=logger)
        log_level = 1
        message = "foobar"
        hl.log(log_level, message)

        self.assertEqual(logger.loglvl, log_level)
        self.assertEqual(logger.msg, message)


class TestUndoHardlinkClass(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_undo_hardlink(self):
        path_src = os.path.join(self.tmp_dir, "a")
        path_dst = os.path.join(self.tmp_dir, "b")
        open(path_src, 'w').write("asdf")
        old_stat = os.stat(path_src)

        # Only one hardlink exists
        uhl1 = UndoHardlink()
        uhl1.undo_hardlink(path_src)
        new_stat = os.stat(path_src)
        self.assertEqual(old_stat.st_nlink, new_stat.st_nlink)

        # Two hardlinks exist
        os.link(path_src, path_dst)
        uhl2 = UndoHardlink()
        uhl2.undo_hardlink(path_dst)
        new_stat = os.stat(path_dst)
        self.assertNotEqual(old_stat.st_ino, new_stat.st_ino)
        self.assertEqual(new_stat.st_nlink, 1) # Expected num of hardlinks is 1
