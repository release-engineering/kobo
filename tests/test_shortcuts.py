#!/usr/bin/python
# -*- coding: utf-8 -*-


import mock
import unittest
import pytest

import os
import sys
import shutil
import tempfile
from six.moves import StringIO

from kobo.shortcuts import force_list, force_tuple, allof, anyof, noneof, oneof, is_empty, iter_chunks, save_to_file, read_from_file, run, read_checksum_file, compute_file_checksums, makedirs, split_path, relative_path
from six.moves import range


class TestShortcuts(unittest.TestCase):
    def test_force_list(self):
        self.assertEqual(force_list("a"), ["a"])
        self.assertEqual(force_list(["a"]), ["a"])
        self.assertEqual(force_list(["a", "b"]), ["a", "b"])
        self.assertCountEqual(force_list({'a': True, 'b': True}.keys()), ["a", "b"])
        self.assertCountEqual(force_list(set(["a", "b"])), ["a", "b"])

    def test_force_tuple(self):
        self.assertEqual(force_tuple("a"), ("a",))
        self.assertEqual(force_tuple(("a",)), ("a",))
        self.assertEqual(force_tuple(("a", "b")), ("a", "b"))
        self.assertCountEqual(force_tuple({'a': True, 'b': True}.keys()), ("a", "b"))
        self.assertCountEqual(force_tuple(set(["a", "b"])), ("a", "b"))

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
        self.assertEqual(list(iter_chunks(list(range(5)), 1)), [[0], [1], [2], [3], [4]])
        self.assertEqual(list(iter_chunks(list(range(5)), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(iter_chunks(list(range(5)), 5)), [[0, 1, 2, 3, 4]])
        self.assertEqual(list(iter_chunks(list(range(6)), 2)), [[0, 1], [2, 3], [4, 5]])

        self.assertEqual(list(iter_chunks(range(5), 2)), [[0, 1], [2, 3], [4]])
        self.assertEqual(list(iter_chunks(range(6), 2)), [[0, 1], [2, 3], [4, 5]])
        self.assertEqual(list(iter_chunks(range(1, 6), 2)), [[1, 2], [3, 4], [5]])
        self.assertEqual(list(iter_chunks(range(1, 7), 2)), [[1, 2], [3, 4], [5, 6]])

        def gen(num):
            for i in range(num):
                yield i+1
        self.assertEqual(list(iter_chunks(gen(5), 2)), [[1, 2], [3, 4], [5]])

        self.assertEqual(list(iter_chunks("01234", 2)), ["01", "23", "4"])
        self.assertEqual(list(iter_chunks("012345", 2)), ["01", "23", "45"])

        file_obj = open(os.path.dirname(os.path.abspath(__file__)) + "/chunks_file", "r")
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
        self.assertEqual(os.stat(self.tmp_file).st_mode & 0o777, 0o644)

        os.unlink(self.tmp_file)
        save_to_file(self.tmp_file, "foo", append=True, mode=0o600)
        self.assertEqual(os.stat(self.tmp_file).st_mode & 0o777, 0o600)

    def test_run(self):
        ret, out = run("echo hello")
        self.assertEqual(ret, 0)
        self.assertEqual(out, b"hello\n")

        ret, out = run(["echo", "'hello'"])
        self.assertEqual(ret, 0)
        self.assertEqual(out, b"'hello'\n")

        ret, out = run(["echo", "\" ' "])
        self.assertEqual(ret, 0)
        self.assertEqual(out, b"\" ' \n")

        # test a longer output that needs to be read in several chunks
        ret, out = run("echo -n '%s'; sleep 0.2; echo -n '%s'" % (10000 * "x", 10 * "a"), logfile=self.tmp_file, can_fail=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 10000 * b"x" + 10 * b"a")
        # check if log file is written properly; it is supposed to append data to existing content
        self.assertEqual("\n".join(read_from_file(self.tmp_file)), "test" + 10000 * "x" + 10 * "a")

        ret, out = run("exit 1", can_fail=True)
        self.assertEqual(ret, 1)

        self.assertRaises(RuntimeError, run, "exit 1")

        # stdin test
        ret, out = run("xargs -0 echo -n", stdin_data=b"\0".join([str(i).encode() for i in range(10000)]))
        self.assertEqual(out, b" ".join([str(i).encode() for i in range(10000)]))

        # return None
        ret, out = run("xargs echo", stdin_data=b"\n".join([str(i).encode() for i in range(1000000)]), return_stdout=False)
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

        self.assertRaises(RuntimeError, run, "commanddoesnotexists")

        # bashism - output redirection to subshells
        run("echo foo | tee >(md5sum -b) >/dev/null", executable="/bin/bash")

    @pytest.mark.xfail(sys.version_info < (3, 7), reason="python3.7 api changes")
    def test_run_in_text_mode(self):
        """test run with kwargs 'text', 'encoding' or/and 'errors' set. These kwargs are
        added to Popen from python3.6(encoding, errors) and python3.7(text). Running test
        with python version older than 3.7 is expected to fail
        """
        ret, out = run("echo hello", text=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, "hello\n")

        ret, out = run("echo hello", encoding="utf-8")
        self.assertEqual(ret, 0)
        self.assertEqual(out, "hello\n")

        ret, out = run("echo hello", errors="strict")
        self.assertEqual(ret, 0)
        self.assertEqual(out, "hello\n")

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_univ_nl_show_cmd_logfile_stdout(self, mock_out):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", universal_newlines=True, show_cmd=True,
                       logfile=logfile, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(),
                             'COMMAND: echo foo\n-----------------\nfoo\n')
        self.assertEqual(mock_out.getvalue(),
                         'COMMAND: echo foo\n-----------------\nfoo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_show_cmd_logfile_stdout(self, mock_out):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", show_cmd=True, logfile=logfile, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(),
                             'COMMAND: echo foo\n-----------------\nfoo\n')
        self.assertEqual(mock_out.getvalue(),
                         'COMMAND: echo foo\n-----------------\nfoo\n')

    def test_run_split_in_middle_of_utf8_sequence(self):
        cmd = "printf ' ' && bash -c \"printf 'č%.0s' {1..10000}\""
        ret, out = run(cmd, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b" " + b"\xc4\x8d" * 10000)

    def test_run_chunk_ends_with_incomplete_char(self):
        cmd = "bash -c \"printf 'a b \\xc4'\""
        self.assertRaises(UnicodeDecodeError, run, cmd, stdout=True)

    def test_run_chunk_with_incomplete_char_in_middle(self):
        cmd = "bash -c \"printf 'a \\xc4 b'\""
        self.assertRaises(UnicodeDecodeError, run, cmd, stdout=True)

    def test_run_other_unicode_decode_error(self):
        cmd = "bash -c \"printf 'a \\x80 b'\""
        self.assertRaises(UnicodeDecodeError, run, cmd, stdout=True)

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_univ_nl_logfile_stdout(self, mock_out):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", universal_newlines=True,
                       logfile=logfile, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(), 'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'foo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_logfile_stdout(self, mock_out):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", logfile=logfile, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(), 'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'foo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_univ_nl_show_cmd_stdout(self, mock_out):
        ret, out = run("echo foo", universal_newlines=True, show_cmd=True,
                       stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'COMMAND: echo foo\n-----------------\nfoo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_show_cmd_stdout(self, mock_out):
        ret, out = run("echo foo", show_cmd=True, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'COMMAND: echo foo\n-----------------\nfoo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_univ_nl_stdout(self, mock_out):
        ret, out = run("echo foo", universal_newlines=True, stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'foo\n')

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_run_stdout(self, mock_out):
        ret, out = run("echo foo", stdout=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        self.assertEqual(mock_out.getvalue(),
                         'foo\n')

    def test_run_univ_nl_show_cmd_logfile(self):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", universal_newlines=True, show_cmd=True,
                       logfile=logfile)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(),
                             'COMMAND: echo foo\n-----------------\nfoo\n')

    def test_run_show_cmd_logfile(self):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", show_cmd=True, logfile=logfile)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(),
                             'COMMAND: echo foo\n-----------------\nfoo\n')

    def test_run_univ_nl_logfile(self):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", universal_newlines=True,
                       logfile=logfile)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(), 'foo\n')

    def test_run_logfile(self):
        logfile = os.path.join(self.tmp_dir, 'output.log')
        ret, out = run("echo foo", logfile=logfile)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')
        with open(logfile) as f:
            self.assertEqual(f.read(), 'foo\n')

    def test_run_univ_nl_show_cmd(self):
        ret, out = run("echo foo", universal_newlines=True, show_cmd=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')

    def test_run_show_cmd(self):
        ret, out = run("echo foo", show_cmd=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, b'foo\n')

    def test_run_univ_nl(self):
        ret, out = run("echo foo", universal_newlines=True)
        self.assertEqual(ret, 0)
        self.assertEqual(out, 'foo\n')

    # Test for all four options False is already contained in test_run.

    def test_run_move_dir_with_logfile(self):
        # Write log into a directory that gets renamed by the called command.
        # The file should be opened just once at the start.
        tmpdir = tempfile.mkdtemp(prefix='kobo-bug-')
        logfile = os.path.join(tmpdir, 'file.log')
        destdir = tmpdir + '.moved'
        run(['mv', '-v', tmpdir, destdir], logfile=logfile, show_cmd=True)
        self.assertTrue(os.path.isfile(os.path.join(destdir, 'file.log')))
        shutil.rmtree(destdir)

    def test_read_checksum_file(self):
        data = r"""01186fcf04b4b447f393e552964c08c7b419c1ad7a25c342a0b631b1967d3a27 *test-data/a b
a63d8014dba891345b30174df2b2a57efbb65b4f9f09b98f245d1b3192277ece *test-data/ab
\911169ddaaf146aff539f58c26c489af3b892dff0fe283c1c264c65ae5aa59a2 *test-data/a\nb
ef743c494c8ed766272eef7992607a843799149252822266adc302547587253d *test-data/a"b
\eaba35b63f3a21c43bc4d579fa4ae0cd388ec8633c08e0a54859d07d33a0c487 *test-data/a\\b"""
        open(self.tmp_file, "w").write(data)

        checksums = read_checksum_file(self.tmp_file)

        checksum, path = checksums[0]
        self.assertEqual(checksum, "01186fcf04b4b447f393e552964c08c7b419c1ad7a25c342a0b631b1967d3a27")
        self.assertEqual(path, "test-data/a b")

        checksum, path = checksums[1]
        self.assertEqual(checksum, "a63d8014dba891345b30174df2b2a57efbb65b4f9f09b98f245d1b3192277ece")
        self.assertEqual(path, "test-data/ab")

        checksum, path = checksums[2]
        self.assertEqual(checksum, "911169ddaaf146aff539f58c26c489af3b892dff0fe283c1c264c65ae5aa59a2")
        self.assertEqual(path, "test-data/a\nb")

        checksum, path = checksums[3]
        self.assertEqual(checksum, "ef743c494c8ed766272eef7992607a843799149252822266adc302547587253d")
        self.assertEqual(path, "test-data/a\"b")

        checksum, path = checksums[4]
        self.assertEqual(checksum, "eaba35b63f3a21c43bc4d579fa4ae0cd388ec8633c08e0a54859d07d33a0c487")
        self.assertEqual(path, "test-data/a\\b")

    def test_compute_file_checksums(self):
        self.assertEqual(compute_file_checksums(self.tmp_file, "md5"), dict(md5="098f6bcd4621d373cade4e832627b4f6"))
        self.assertEqual(compute_file_checksums(self.tmp_file, ["md5", "sha256"]), dict(md5="098f6bcd4621d373cade4e832627b4f6", sha256="9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"))
        self.assertEqual(compute_file_checksums(self.tmp_file, ["md5", "md5"]), dict(md5="098f6bcd4621d373cade4e832627b4f6"))
        self.assertRaises(ValueError, compute_file_checksums, self.tmp_file, "unsupported_checksum")

    def test_makedirs(self):
        path = os.path.join(self.tmp_dir, "dir")
        makedirs(path)
        makedirs(path)

        path = os.path.join(self.tmp_dir, "file")
        open(path, "w").close()
        self.assertRaises(OSError, makedirs, path)


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
