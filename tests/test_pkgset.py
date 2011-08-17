#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import run_tests # set sys.path

import tempfile
import os.path
import shutil
import hashlib

from kobo.pkgset import *


class TestFileWrapperClass(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_file_name_property(self):
        name = "file"
        file1 = os.path.join(self.tmp_dir, name)
        open(file1, "w").write("hello\n")
        wrap = FileWrapper(file1)
        self.assertEqual(wrap.file_name, name)

    def test_compute_checksums(self):
        file1 = os.path.join(self.tmp_dir, "file")
        open(file1, "w").write("hello\n")

        res_origin = {}
        for name in ("md5", "sha1", "sha256", "sha512"):
            m = hashlib.new(name)
            m.update(open(file1, "rb").read())
            res_origin[name] = m.hexdigest()

        wrap = FileWrapper(file1)
        res = wrap.compute_checksums(["md5", "sha1", "sha256", "sha512"])
        self.assertEqual(res_origin, res)


class TestFileCacheClass(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_add_two_same_hardlinks(self):
        file1 = os.path.join(self.tmp_dir, "file_1")
        file2 = os.path.join(self.tmp_dir, "file_2")
        open(file1, "w").write("hello\n")
        os.link(file1, file2)

        cache = FileCache()
        wrap1 = cache.add(file1)
        wrap2 = cache.add(file2)

        self.assertEqual(len(cache), 1)
        self.assertEqual(id(wrap1), id(wrap2))

    def test_add_two_different_files(self):
        file1 = os.path.join(self.tmp_dir, "file_1")
        file2 = os.path.join(self.tmp_dir, "file_2")
        open(file1, "w").write("roses are red\n")
        open(file2, "w").write("violets are blue\n")

        cache = FileCache()
        wrap1 = cache.add(file1)
        wrap2 = cache.add(file2)

        self.assertEqual(len(cache), 2)
        self.assertNotEqual(id(wrap1), id(wrap2))

    def test_getitem(self):
        file1 = os.path.join(self.tmp_dir, "file_1")
        file2 = os.path.join(self.tmp_dir, "file_2")
        open(file1, "w").write("hello\n")
        open(file2, "w").write("hello\n")

        cache = FileCache()
        wrap1 = cache.add(file1)
        wrap2 = cache.add(file2)

        self.assertEqual(id(cache[file1]), id(wrap1))
        self.assertEqual(id(cache[file2]), id(wrap2))

    def test_iteritems(self):
        file1 = os.path.join(self.tmp_dir, "file_1")
        file2 = os.path.join(self.tmp_dir, "file_2")
        open(file1, "w").write("hello\n")
        open(file2, "w").write("hello\n")

        cache = FileCache()
        wrap1 = cache.add(file1)
        wrap2 = cache.add(file2)

        items = [path for path, _ in cache.iteritems()]
        self.assertEqual(len(items), 2)
        self.assertTrue(file1 in items)
        self.assertTrue(file2 in items)

    def test_iter(self):
        file1 = os.path.join(self.tmp_dir, "file_1")
        file2 = os.path.join(self.tmp_dir, "file_2")
        open(file1, "w").write("hello\n")
        open(file2, "w").write("hello\n")

        cache = FileCache()
        wrap1 = cache.add(file1)
        wrap2 = cache.add(file2)

        items = [item for item in cache]

        self.assertEqual(len(items), 2)
        self.assertTrue(file1 in items)
        self.assertTrue(file2 in items)


if __name__ == "__main__":
    unittest.main()
