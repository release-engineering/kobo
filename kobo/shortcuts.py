# -*- coding: utf-8 -*-


import os
import sys
import subprocess
import random
import re


__all__ = (
    "force_list",
    "force_tuple",
    "allof",
    "anyof",
    "noneof",
    "oneof",
    "random_string",
    "hex_string",
    "touch",
    "save",
    "find_symlinks_to",
    "run",
    "parse_checksum_line",
    "read_checksum_file",
)


def force_list(value):
    if type(value) in (list, tuple):
        return list(value)
    return [value]


def force_tuple(value):
    if type(value) in (list, tuple):
        return tuple(value)
    return (value,)


def allof(*args, **kwargs):
    for i in list(args) + kwargs.values():
        if not i:
            return False
    return True


def anyof(*args, **kwargs):
    for i in list(args) + kwargs.values():
        if i:
            return True
    return False


def noneof(*args, **kwargs):
    for i in list(args) + kwargs.values():
        if i:
            return False
    return True


def oneof(*args, **kwargs):
    found = False
    for i in list(args) + kwargs.values():
        if i:
            if found:
                return False
            found = True
    return found


def is_empty(value):
    """Test if value is None, empty string, list, tuple or dict."""
    if value is None:
        return True
    if type(value) in (list, tuple, dict):
        return len(value) == 0
    if not value:
        return True
    return False


def random_string(length=32, alphabet=None):
    alphabet = alphabet or "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join([ random.choice(alphabet) for i in xrange(length) ])


def hex_string(string):
    """Convert a string to a string of hex digits."""
    return "".join(( "%02x" % ord(i) for i in string ))


def touch(filename):
    open(filename, "a").close()


def save(filename, text, append=False):
    if append:
        fo = open(filename, "a+")
    else:
        fo = open(filename, "wb")
    fo.write(text)
    fo.close()


def find_symlinks_to(target, directory):
    target = os.path.abspath(target)
    directory = os.path.abspath(directory)
    result = []
    for fn in os.listdir(directory):
        path = os.path.abspath(os.path.join(directory, fn))

        if not os.path.islink(path):
            continue

        if os.path.abspath(os.path.join(directory, os.path.normpath(os.readlink(path)))) == os.path.abspath(target):
            result.append(path)

    return result


def run(cmd, show_cmd=False, stdout=False, logfile=None, can_fail=False, workdir=None):
    """Run a command in shell and return (returncode, merged stdout+stderr)."""

    cwd = os.getcwd()
    if workdir is not None:
        os.chdir(workdir)

    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    proc.wait()
    output = proc.stdout.read()

    command = "COMMAND: %s\n%s\n" % (cmd, "-" * (len(cmd)+9))

    if stdout:
        if show_cmd:
            print command,
        print output

    if logfile:
        if show_cmd:
            save(logfile, command)
            save(logfile, output, append=True)
        else:
            save(logfile, output)

    if workdir is not None:
        os.chdir(cwd)

    err_msg = "ERROR running command: %s" % cmd
    if proc.returncode != 0 and show_cmd:
        print >> sys.stderr, err_msg

    if proc.returncode != 0 and not can_fail:
        raise RuntimeError(err_msg)

    return (proc.returncode, output)


CHECKSUM_FILE_RE = re.compile("^(?P<checksum>\w+) [ \*](?P<path>.*)$")
def parse_checksum_line(line):
    """Parse a line of md5sum, sha256sum, ... file. Return (checksum, path)."""

    line = line.replace("\n", "").replace("\r", "")
    if line.strip() == "":
        return None
        
    match = CHECKSUM_FILE_RE.match(line)
    if match is None:
        return None

    return match.groups()


def read_checksum_file(file_name):
    """Read checksums from a file. Return [(checksum, path)]."""
    result = []
    fo = open(file_name, "rb")
    
    for line in fo:
        checksum_tuple = parse_checksum_line(line)
        if checksum_tuple is not None:
            result.append(checksum_tuple)
        
    fo.close()
    return result
