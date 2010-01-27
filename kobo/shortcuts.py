# -*- coding: utf-8 -*-


"""
Various useful shortcuts.
"""


import os
import sys
import subprocess
import random
import re
import hashlib


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
    "read_from_file",
    "save",
    "save_to_file",
    "find_symlinks_to",
    "run",
    "compute_file_checksums",
    "parse_checksum_line",
    "read_checksum_file",
)


def force_list(value):
    """Convert a value to list.

    @rtype: list
    """
    if type(value) in (list, tuple):
        return list(value)
    return [value]


def force_tuple(value):
    """Convert a value to tuple.

    @rtype: tuple
    """
    if type(value) in (list, tuple):
        return tuple(value)
    return (value, )


def allof(*args, **kwargs):
    """Test if all values are True.

    @rtype: bool
    """
    for i in list(args) + kwargs.values():
        if not i:
            return False
    return True


def anyof(*args, **kwargs):
    """Test if at least one of the values is True.

    @rtype: bool
    """
    for i in list(args) + kwargs.values():
        if i:
            return True
    return False


def noneof(*args, **kwargs):
    """Test if all values are False.

    @rtype: bool
    """
    for i in list(args) + kwargs.values():
        if i:
            return False
    return True


def oneof(*args, **kwargs):
    """Test if just one of the values is True.

    @rtype: bool
    """
    found = False
    for i in list(args) + kwargs.values():
        if i:
            if found:
                return False
            found = True
    return found


def is_empty(value):
    """Test if value is None, empty string, list, tuple or dict.

    @rtype: bool
    """
    if value is None:
        return True
    if type(value) in (list, tuple, dict):
        return len(value) == 0
    if not value:
        return True
    return False


def random_string(length=32, alphabet=None):
    """Return random string of given lenght which consists of characters from the alphabet.

    @rtype: str
    """
    alphabet = alphabet or "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join([ random.choice(alphabet) for i in xrange(length) ])


def hex_string(string):
    """Convert a string to a string of hex digits.

    @rtype: str
    """
    return "".join(( "%02x" % ord(i) for i in string ))


def touch(filename):
    """Touch a file."""
    open(filename, "a").close()



def read_from_file(filename, lines=None, re_filter=None):
    """Read a text file."""
    result = []
    fo = open(filename, "rt")

    if re_filter is not None:
        re_filter_compiled = re.compile(re_filter)

    for i, line in enumerate(fo):
        if lines is not None and i+1 not in lines:
            continue
        line = line.rstrip("\r\n")
        if re_filter is not None and not re_filter_compiled.match(line):
            continue
        result.append(line)

    fo.close()
    return result


def save_to_file(filename, text, append=False, mode=0644):
    """Save text to a file."""
    if append and os.path.exists(filename):
        fd = os.open(filename, os.O_RDWR | os.O_APPEND, mode)
    else:
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    os.write(fd, text)
    os.close(fd)


def save(*args, **kwargs):
    print >> sys.stderr, "DeprecationWarning: kobo.shortcuts.save() is deprecated, use kobo.shortcuts.save_to_file() instead."
    return save_to_file(*args, **kwargs)


def find_symlinks_to(target, directory):
    """Find symlinks which point to a target.

    @param target: the symlink target we're looking for
    @type target: str
    @param directory: directory with symlinks
    @type directory: str
    @return: list of symlinks to the target
    @rtype: list
    """

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
    """Run a command in shell.

    @param show_cmd: show command in stdout/log
    @type show_cmd: bool
    @param stdout: print output to stdout
    @type stdout: bool
    @param logfile: save output to logfile
    @type logfile: str
    @return: (command return code, merged stdout+stderr)
    @rtype: (int, str)
    """

    cwd = os.getcwd()
    if workdir is not None:
        os.chdir(workdir)

    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ""
    while proc.poll() is None:
        output += proc.stdout.read()

    output += proc.stdout.read()

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


def compute_file_checksums(filename, checksum_types):
    """
    Compute a file checksum of given type.
    Checksum must be supported by hashlib.

    @param filename: path to a file
    @type filename: str
    @param checksum_type: checksum types, supported by hashlib
    @type checksum_type: str or list
    @return: {checksum_type: digest in lowercase hex}
    @rtype: dict
    """

    checksum_types = force_tuple(checksum_types)
    checksums = {}

    for checksum_type in checksum_types:
        try:
            checksums[checksum_type] = getattr(hashlib, checksum_type)()
        except ValueError:
            raise ValueError("Checksum is not supported in hashlib: %s" % checksum_type)

    fo = open(filename, "r")
    while True:
        chunk = fo.read(1024**2)
        if not chunk:
            break
        for checksum_type in checksum_types:
            checksums[checksum_type].update(chunk)
    fo.close()

    result = {}
    for checksum_type, checksum in checksums.iteritems():
        result[checksum_type] = checksum.hexdigest().lower()
    return result


CHECKSUM_FILE_RE = re.compile("^(?P<checksum>\w+) [ \*](?P<path>.*)$")
def parse_checksum_line(line):
    """Parse a line of md5sum, sha256sum, ... file.

    @param line: line of a *sum file
    @type line: str
    @return: (checksum, path)
    @rtype: (str, str)
    """

    line = line.replace("\n", "").replace("\r", "")
    if line.strip() == "":
        return None

    match = CHECKSUM_FILE_RE.match(line)
    if match is None:
        return None

    return match.groups()


def read_checksum_file(file_name):
    """Read checksums from a file.

    @param file_name: checksum file
    @type file_name: str
    @return [(checksum, path)]
    @rtype: [(str, str)]
    """

    result = []
    fo = open(file_name, "rb")

    for line in fo:
        checksum_tuple = parse_checksum_line(line)
        if checksum_tuple is not None:
            result.append(checksum_tuple)

    fo.close()
    return result
