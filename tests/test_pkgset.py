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
        self.cache = FileCache()
        self.file1 = os.path.join(self.tmp_dir, "file_1")
        self.file2 = os.path.join(self.tmp_dir, "file_2")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_add_two_same_hardlinks(self):
        open(self.file1, "w").write("hello\n")
        os.link(self.file1, self.file2)

        self.cache = FileCache()
        wrap1 = self.cache.add(self.file1)
        wrap2 = self.cache.add(self.file2)

        self.assertEqual(len(self.cache.inode_cache), 1)
        self.assertEqual(len(self.cache.file_cache), 1)
        self.assertEqual(len(self.cache), 1)
        self.assertEqual(id(wrap1), id(wrap2))

    def test_add_two_different_files(self):
        open(self.file1, "w").write("roses are red\n")
        open(self.file2, "w").write("violets are blue\n")

        self.cache = FileCache()
        wrap1 = self.cache.add(self.file1)
        wrap2 = self.cache.add(self.file2)

        self.assertEqual(len(self.cache.inode_cache), 2)
        self.assertEqual(len(self.cache.file_cache), 2)
        self.assertEqual(len(self.cache), 2)
        self.assertNotEqual(id(wrap1), id(wrap2))

    def test_getitem(self):
        open(self.file1, "w").write("hello\n")
        open(self.file2, "w").write("hello\n")

        self.cache = FileCache()
        wrap1 = self.cache.add(self.file1)
        wrap2 = self.cache.add(self.file2)

        self.assertEqual(len(self.cache.inode_cache), 2)
        self.assertEqual(len(self.cache.file_cache), 2)
        self.assertEqual(id(self.cache[self.file1]), id(wrap1))
        self.assertEqual(id(self.cache[self.file2]), id(wrap2))

    def test_iteritems(self):
        open(self.file1, "w").write("hello\n")
        open(self.file2, "w").write("hello\n")

        self.cache = FileCache()
        wrap1 = self.cache.add(self.file1)
        wrap2 = self.cache.add(self.file2)

        items = [path for path, _ in self.cache.iteritems()]

        self.assertEqual(len(self.cache.inode_cache), 2)
        self.assertEqual(len(self.cache.file_cache), 2)
        self.assertEqual(len(items), 2)
        self.assertTrue(self.file1 in items)
        self.assertTrue(self.file2 in items)

    def test_iter(self):
        open(self.file1, "w").write("hello\n")
        open(self.file2, "w").write("hello\n")

        self.cache = FileCache()
        wrap1 = self.cache.add(self.file1)
        wrap2 = self.cache.add(self.file2)

        items = [item for item in self.cache]

        self.assertEqual(len(self.cache.inode_cache), 2)
        self.assertEqual(len(self.cache.file_cache), 2)
        self.assertEqual(len(items), 2)
        self.assertTrue(self.file1 in items)
        self.assertTrue(self.file2 in items)

    def test_remove_by_file_path(self):
        self.test_add_two_different_files()
        self.cache.remove(self.file1)

        items = [item for item in self.cache]

        self.assertEqual(len(self.cache.inode_cache), 1)
        self.assertEqual(len(self.cache.file_cache), 1)
        self.assertEqual(len(items), 1)
        self.assertTrue(self.file1 not in items)
        self.assertTrue(self.file2 in items)

    def test_remove_by_obj(self):
        self.test_add_two_different_files()

        self.file1_obj = self.cache[self.file1]
        self.cache.remove(self.file1_obj)

        items = [item for item in self.cache]

        self.assertEqual(len(self.cache.inode_cache), 1)
        self.assertEqual(len(self.cache.file_cache), 1)
        self.assertEqual(len(items), 1)
        self.assertTrue(self.file1 not in items)
        self.assertTrue(self.file2 in items)

    def test_remove_by_filenames(self):
        self.test_add_two_different_files()

        # add a file with existing name to a subdir
        os.makedirs(os.path.join(self.tmp_dir, "dir"))
        file1a = os.path.join(self.tmp_dir, "dir", "file_1")
        open(file1a, "w").write("hello\n")
        self.cache.add(file1a)

        self.cache.remove_by_filenames("does-not-exist")
        self.assertEqual(len(self.cache.inode_cache), 3)
        self.assertEqual(len(self.cache.file_cache), 3)

        # ignores the path, only the file name is important
        # removes both files with the file name "file_1"
        self.cache.remove_by_filenames("/foo/bar/file_1")

        items = [item for item in self.cache]

        self.assertEqual(len(self.cache.inode_cache), 1)
        self.assertEqual(len(self.cache.file_cache), 1)
        self.assertEqual(len(items), 1)
        self.assertTrue(self.file1 not in items)
        self.assertTrue(self.file2 in items)


if __name__ == "__main__":
    unittest.main()
