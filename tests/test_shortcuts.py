#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import run_tests # set sys.path

import os
import shutil
import tempfile
from cStringIO import StringIO

from kobo.shortcuts import *


class TestShortcuts(unittest.TestCase):
    def test_force_list(self):
        self.assertEqual(force_list("a"), ["a"])
        self.assertEqual(force_list(["a"]), ["a"])
        self.assertEqual(force_list(["a", "b"]), ["a", "b"])
        self.assertEqual(force_list(set(["a", "b"])), ["a", "b"])

    def test_force_tuple(self):
        self.assertEqual(force_tuple("a"), ("a",))
        self.assertEqual(force_tuple(("a",)), ("a",))
        self.assertEqual(force_tuple(("a", "b")), ("a", "b"))
        self.assertEqual(force_tuple(set(["a", "b"])), ("a", "b"))

    def test_allof(self):
        self.assertEqual(allof(), True)
        self.assertEqual(allof(1), True)
        self.assertEqual(allof(True), True)
        self.assertEqual(allof(True, 1, "a"), True)
        self.assertEqual(allof(0), False)
        self.assertEqual(allof(""), False)
        self.assertEqual(allof(None), False)

    def test_anyof(self):
        self.assertEqual(anyof(), False)
        self.assertEqual(anyof(1), True)
        self.assertEqual(anyof(True), True)
        self.assertEqual(anyof(True, 0, "a"), True)
        self.assertEqual(anyof(0), False)
        self.assertEqual(anyof(""), False)
        self.assertEqual(anyof(None), False)

    def test_noneof(self):
        self.assertEqual(noneof(), True)
        self.assertEqual(noneof(False), True)
        self.assertEqual(noneof(True), False)
        self.assertEqual(noneof(False, "", 0), True)
        self.assertEqual(noneof(True, "a", 1), False)
        self.assertEqual(noneof(False, "a", 1), False)
        self.assertEqual(noneof(0, True, False, "a"), False)

    def test_oneof(self):
        self.assertEqual(oneof(), False)
        self.assertEqual(oneof(True), True)
        self.assertEqual(oneof(False), False)
        self.assertEqual(oneof(0, False, "a"), True)
        self.assertEqual(oneof(0, True, False, "a"), False)
        self.assertEqual(oneof(1, True, "a"), False)
        self.assertEqual(oneof(0, False, ""), False)

    def test_is_empty(self):
        self.assertEqual(is_empty(None), True)
        self.assertEqual(is_empty([]), True)
        self.assertEqual(is_empty([1]), False)
        self.assertEqual(is_empty(()), True)
        self.assertEqual(is_empty((1,)), False)
        self.assertEqual(is_empty({}), True)
        self.assertEqual(is_empty(1), False)

    def test_iter_chunks(self):
        self.assertEqual(list(iter_chunks([], 100)), [])
        self.assertEqual(list(iter_chunks(range(5), 1)), [[0], [1], [2], [3], [4]])
        self.assertEqual(list(iter_chunks(range(5), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(iter_chunks(range(5), 5)), [[0, 1, 2, 3, 4]])
        self.assertEqual(list(iter_chunks(range(6), 2)), [[0, 1], [2, 3], [4, 5]])

        self.assertEqual(list(iter_chunks(xrange(5), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(iter_chunks(xrange(6), 2)), [[0, 1], [2, 3], [4, 5]])
        self.assertEqual(list(iter_chunks(xrange(1, 6), 2)), [[1, 2], [3, 4], [5]])
        self.assertEqual(list(iter_chunks(xrange(1, 7), 2)), [[1, 2], [3, 4], [5, 6]])

        def gen(num):
            for i in xrange(num):
                yield i+1
        self.assertEqual(list(iter_chunks(gen(5), 2)), [[1, 2], [3, 4], [5]])

        self.assertEqual(list(iter_chunks("01234", 2)), ["01", "23", "4"])
        self.assertEqual(list(iter_chunks("012345", 2)), ["01", "23", "45"])

        file_obj = open("chunks_file", "r")
        self.assertEqual(list(iter_chunks(file_obj, 11)), (10 * ["1234567890\n"]) + ["\n"])

        string_io = StringIO((10 * "1234567890\n") + "\n")
        self.assertEqual(list(iter_chunks(string_io, 11)), (10 * ["1234567890\n"]) + ["\n"])


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_file = os.path.join(self.tmp_dir, "tmp_file")
        save_to_file(self.tmp_file, "test")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_save_to_file(self):
        save_to_file(self.tmp_file, "foo")
        self.assertEqual("\n".join(read_from_file(self.tmp_file)), "foo")

        save_to_file(self.tmp_file, "\nbar", append=True, mode=600)
        self.assertEqual("\n".join(read_from_file(self.tmp_file)), "foo\nbar")

        # append doesn't modify existing perms
        self.assertEqual(os.stat(self.tmp_file).st_mode & 0777, 0644)

        os.unlink(self.tmp_file)
        save_to_file(self.tmp_file, "foo", append=True, mode=0600)
        self.assertEqual(os.stat(self.tmp_file).st_mode & 0777, 0600)

    def test_run(self):
        ret, out = run("echo hello")
        self.assertEqual(ret, 0)
        self.assertEqual(out, "hello\n")

        ret, out = run(["echo", "'hello'"])
        self.assertEqual(ret, 0)
        self.assertEqual(out, "'hello'\n")

        ret, out = run(["echo", "\" ' "])
        self.assertEqual(ret, 0)
        self.assertEqual(out, "\" ' \n")

        # test a longer output that needs to be read in several chunks
        ret, out = run("echo -n '%s'; sleep 0.2; echo -n '%s'" % (10000 * "x", 10 * "a"), logfile=self.tmp_file, can_fail=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 10000 * "x" + 10 * "a")
        # check if log file is written properly; it is supposed to append data to existing content
        self.assertEqual("\n".join(read_from_file(self.tmp_file)), "test" + 10000 * "x" + 10 * "a")

        ret, out = run("exit 1", can_fail=True)
        self.assertEqual(ret, 1)

        self.assertRaises(RuntimeError, run, "exit 1")

        # stdin test
        ret, out = run("xargs -0 echo -n", stdin_data="\0".join([str(i) for i in xrange(10000)]))
        self.assertEqual(out, " ".join([str(i) for i in xrange(10000)]))

        # return None
        ret, out = run("xargs echo", stdin_data="\n".join([str(i) for i in xrange(1000000)]), return_stdout=False)
        self.assertEqual(out, None)

        # log file with absolute path
        log_file = os.path.join(self.tmp_dir, "a.log")
        ret, out = run("echo XXX", logfile=log_file)
        self.assertEqual(open(log_file, "r").read(), "XXX\n")

        # log file with relative path
        log_file = "b.log"
        cwd = os.getcwd()
        os.chdir(self.tmp_dir)
        ret, out = run("echo XXX", logfile=log_file)
        self.assertEqual(open(log_file, "r").read(), "XXX\n")
        os.chdir(cwd)

    def test_parse_checksum_line(self):
        line_text = "d4e64fc7f3c6849888bc456d77e511ca  shortcuts.py"
        checksum, path = parse_checksum_line(line_text)
        self.assertEqual(checksum, "d4e64fc7f3c6849888bc456d77e511ca")
        self.assertEqual(path, "shortcuts.py")

        line_binary = "d4e64fc7f3c6849888bc456d77e511ca *shortcuts.py"
        checksum, path = parse_checksum_line(line_binary)
        self.assertEqual(checksum, "d4e64fc7f3c6849888bc456d77e511ca")
        self.assertEqual(path, "shortcuts.py")

    def test_compute_file_checksums(self):
        self.assertEqual(compute_file_checksums(self.tmp_file, "md5"), dict(md5="098f6bcd4621d373cade4e832627b4f6"))
        self.assertEqual(compute_file_checksums(self.tmp_file, ["md5", "sha256"]), dict(md5="098f6bcd4621d373cade4e832627b4f6", sha256="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))


class TestPaths(unittest.TestCase):
    def test_split_path(self):
        self.assertEqual(split_path(""), ["."])
        self.assertEqual(split_path("../"), [".."])
        self.assertEqual(split_path("/"), ["/"])
        self.assertEqual(split_path("//"), ["/"])
        self.assertEqual(split_path("///"), ["/"])
        self.assertEqual(split_path("/foo"), ["/", "foo"])
        self.assertEqual(split_path("/foo/"), ["/", "foo"])
        self.assertEqual(split_path("/foo//"), ["/", "foo"])
        self.assertEqual(split_path("/foo/bar"), ["/", "foo", "bar"])
        self.assertEqual(split_path("/foo//bar"), ["/", "foo", "bar"])

    def test_relative_path(self):
        self.assertEqual(relative_path("/foo", "/"), "foo")
        self.assertEqual(relative_path("/foo/", "/"), "foo/")
        self.assertEqual(relative_path("/foo", "/bar/"), "../foo")
        self.assertEqual(relative_path("/foo/", "/bar/"), "../foo/")
        self.assertEqual(relative_path("/var/www/template/index.html", "/var/www/html/index.html"), "../template/index.html")
        self.assertEqual(relative_path("/var/www/template/index.txt", "/var/www/html/index.html"), "../template/index.txt")
        self.assertEqual(relative_path("/var/www/template/index.txt", "/var/www/html/index.html"), "../template/index.txt")
        self.assertRaises(RuntimeError, relative_path, "/var/www/template/", "/var/www/html/index.html")


if __name__ == '__main__':
    unittest.main()
