# -*- coding: utf-8 -*-


"""
Various useful shortcuts.
"""


from __future__ import print_function
import os
import sys
import subprocess
import random
import re
import hashlib
import threading
import locale
import codecs
import six
from six.moves import range
from six.moves import shlex_quote

__all__ = (
    "force_list",
    "force_tuple",
    "allof",
    "anyof",
    "noneof",
    "oneof",
    "is_empty",
    "iter_chunks",
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
    "split_path",
    "relative_path",
    "makedirs",
)


def force_list(value):
    """Convert a value to list.

    @rtype: list
    """
    if type(value) is list:
        return value
    if type(value) in (tuple, set):
        return list(value)
    return [value]


def force_tuple(value):
    """Convert a value to tuple.

    @rtype: tuple
    """
    if type(value) is tuple:
        return value
    if type(value) in (list, set):
        return tuple(value)
    return (value, )


def allof(*args, **kwargs):
    """Test if all values are True.

    @rtype: bool
    """
    for i in list(args) + list(kwargs.values()):
        if not i:
            return False
    return True


def anyof(*args, **kwargs):
    """Test if at least one of the values is True.

    @rtype: bool
    """
    for i in list(args) + list(kwargs.values()):
        if i:
            return True
    return False


def noneof(*args, **kwargs):
    """Test if all values are False.

    @rtype: bool
    """
    for i in list(args) + list(kwargs.values()):
        if i:
            return False
    return True


def oneof(*args, **kwargs):
    """Test if just one of the values is True.

    @rtype: bool
    """
    found = False
    for i in list(args) + list(kwargs.values()):
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


def iter_chunks(input_list, chunk_size):
    """Iterate through input_list and yield chunk_size-d chunks."""

    is_file = hasattr(input_list, "read") and hasattr(input_list, "close") and hasattr(input_list, "seek")
    if is_file:
        while 1:
            chunk = input_list.read(chunk_size)
            if not chunk:
                break
            yield chunk
        return

    # TODO: any idea how to detect generators better?
    if hasattr(input_list, "__iter__") and not isinstance(input_list, six.string_types):
        chunk = []
        for i in input_list:
            chunk.append(i)
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
        return

    for i in range(0, len(input_list), chunk_size):
        yield input_list[i:i + chunk_size]


def random_string(length=32, alphabet=None):
    """Return random string of given lenght which consists of characters from the alphabet.

    @rtype: str
    """
    alphabet = alphabet or "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join([ random.choice(alphabet) for i in range(length) ])


def hex_string(string):
    """Convert a string to a string of hex digits.

    @rtype: str
    """
    return "".join(( "%02x" % ord(i) for i in string ))


def touch(filename, mode=0o644):
    """Touch a file."""
    save_to_file(filename, "", append=True, mode=mode)


def read_from_file(filename, lines=None, re_filter=None, mode='rt'):
    """Read a text file."""
    # Use bytes for stipping when using binary mode
    if 'b' in mode:
        strip = b"\r\n"
    else:
        strip = "\r\n"

    result = []
    fo = open(filename, mode)

    if re_filter is not None:
        re_filter_compiled = re.compile(re_filter)

    for i, line in enumerate(fo):
        if lines is not None and i+1 not in lines:
            continue
        line = line.rstrip(strip)
        if re_filter is not None and not re_filter_compiled.match(line):
            continue
        result.append(line)

    fo.close()
    return result


def save_to_file(filename, text, append=False, mode=0o644):
    """Save text to a file."""
    if append and os.path.exists(filename):
        fd = os.open(filename, os.O_RDWR | os.O_APPEND, mode)
    else:
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    if not isinstance(text, bytes):
        text = bytes(text, encoding=locale.getpreferredencoding())
    os.write(fd, text)
    os.close(fd)


def save(*args, **kwargs):
    print("DeprecationWarning: kobo.shortcuts.save() is deprecated, use kobo.shortcuts.save_to_file() instead.", file=sys.stderr)
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


def run(cmd, show_cmd=False, stdout=False, logfile=None, can_fail=False, workdir=None, stdin_data=None, return_stdout=True, buffer_size=4096, **kwargs):
    """Run a command in shell.

    @param show_cmd: show command in stdout/log
    @type show_cmd: bool
    @param stdout: print output to stdout
    @type stdout: bool
    @param logfile: save output to logfile
    @type logfile: str
    @param can_fail: when set, retcode is returned instead of raising RuntimeError
    @type can_fail: bool
    @param workdir: change current directory to workdir before starting a command
    @type workdir: str
    @param stdin_data: stdin data passed to a command
    @type stdin_data: str
    @param buffer_size: size of buffer for reading from proc's stdout, use -1 for line-buffering
    @type buffer_size: int
    @return_stdout: return command stdout as a function result (turn off when working with large data, None is returned instead of stdout);
                    the command must output valid UTF-8
    @return_stdout: bool
    @return: (command return code, merged stdout+stderr)
    @rtype: (int, str) or (int, None)
    """
    if type(cmd) in (list, tuple):
        cmd = " ".join((shlex_quote(i) for i in cmd))

    # True if Popen and run are operating in text mode (returning str rather than bytes).
    # We need to accurately reproduce Popen behavior here, see:
    # https://docs.python.org/3/library/subprocess.html#subprocess.run
    #
    # Note that this determines the output type, but the process must still
    # produce valid UTF-8 regardless.
    text_mode = (
        kwargs.get('universal_newlines', False)
        or kwargs.get('text', False)
        or kwargs.get('encoding', False)
        or kwargs.get('errors', False)
    )

    log = None
    if logfile:
        logfile = os.path.join(workdir or "", logfile)
        # What happens to log file if it exists already? If show_cmd is True,
        # it will be overwritten. Otherwise the command output will just be
        # appended to the existing file.
        mode = 'a' if not show_cmd and os.path.exists(logfile) else 'w'
        if not text_mode:
            mode += 'b'
        log = open(logfile, mode)

    try:

        if show_cmd:
            command = "COMMAND: %s\n%s\n" % (
                cmd,
                "-" * min(len(cmd) + 9, 79)
            )
            if stdout:
                print(command, end='')
            if logfile:
                if six.PY3 and not text_mode:
                    # Log file opened as binary, encode the command
                    command = bytes(command, encoding='utf-8')
                log.write(command)

        stdin = None
        if stdin_data is not None:
            stdin = subprocess.PIPE

        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=stdin,
                                cwd=workdir, **kwargs)

        if stdin_data is not None:
            class StdinThread(threading.Thread):
                def run(self):
                    proc.stdin.write(stdin_data)
                    proc.stdin.close()
            stdin_thread = StdinThread()
            stdin_thread.daemon = True
            stdin_thread.start()

        # Get a reader for stdout which provides unicode rather than bytes.
        # In text_mode case, that's what proc.stdout is already:
        out_reader = proc.stdout

        # Otherwise, we can wrap it. Note we only support UTF-8.
        if not text_mode:
            out_reader = codecs.getreader('utf-8')(out_reader)

        output = ""
        sentinel = ""
        while True:
            if buffer_size == -1:
                lines = out_reader.readline()
            else:
                try:
                    lines = out_reader.read(buffer_size)
                except (IOError, OSError) as ex:
                    import errno
                    if ex.errno == errno.EINTR:
                        continue
                    else:
                        raise

            if lines == sentinel:
                break
            if stdout:
                sys.stdout.write(lines)
            if logfile:
                log.write(lines)
            if return_stdout:
                output += lines
        proc.wait()

    finally:
        if logfile:
            log.close()

    if stdin_data is not None:
        stdin_thread.join()

    err_msg = "ERROR running command: %s" % cmd
    if logfile:
        err_msg += "\nFor more details see %s" % logfile

    if proc.returncode != 0 and not can_fail:
        exc = RuntimeError(err_msg)
        exc.output = output
        raise exc

    if proc.returncode != 0 and show_cmd:
        print(err_msg, file=sys.stderr)

    if not return_stdout:
        output = None
    elif not text_mode:
        # run() acts like Popen with respect to the return type,
        # which means it should return bytes if not in text mode.
        # We already know that UTF8 is the correct encoding
        # because we'd have crashed earlier if proc.stdout wasn't UTF-8.
        output = output.encode('utf-8')

        # If there was any data left over in the reader's buffer, it means
        # we got an incomplete sequence. Make sure an exception is raised
        # in that case so the problem is detected.
        if out_reader.bytebuffer:
            out_reader.bytebuffer.decode('utf-8')

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

    checksum_types = set(force_tuple(checksum_types))
    checksums = {}

    for checksum_type in checksum_types:
        try:
            checksums[checksum_type] = getattr(hashlib, checksum_type)()
        except AttributeError:
            raise ValueError("Checksum is not supported in hashlib: %s" % checksum_type)

    fo = open(filename, "rb")
    while True:
        chunk = fo.read(1024**2)
        if not chunk:
            break
        for checksum_type in checksum_types:
            checksums[checksum_type].update(chunk)
    fo.close()

    result = {}
    for checksum_type, checksum in six.iteritems(checksums):
        result[checksum_type] = checksum.hexdigest().lower()
    return result


CHECKSUM_LINE_RE = re.compile(r"^(?P<escaped>\\)?(?P<checksum>\S+) [ \*](?P<path>.*)$")
def parse_checksum_line(line):
    """Parse a line of md5sum, sha256sum, ... file.

    @param line: line of a *sum file
    @type line: str
    @return: (checksum, path)
    @rtype: (str, str)
    """

    if isinstance(line, six.binary_type):
        line = line.decode()

    if not line.strip():
        return None
    if line.strip().startswith("#"):
        return None

    match = CHECKSUM_LINE_RE.match(line)
    data = match.groupdict()
    if data["escaped"]:
        try:
            data["path"] = data["path"].decode('string-escape')
        except AttributeError:
            data["path"] = bytes(data["path"], "utf-8").decode('unicode_escape')
    return (data["checksum"], data["path"])


def read_checksum_file(file_name):
    """Read checksums from a file.

    @param file_name: checksum file
    @type file_name: str
    @return: [(checksum, path)]
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


def split_path(path):
    """Split path to a list.

    @param path: a path
    @type path: str
    @return: list with path elements
    @rtype: list
    """

    head, tail = os.path.split(os.path.normpath(path))
    if not head:
        return [tail]
    if not tail:
        if head == os.sep:
            return [head]
        return split_path(head[:-len(os.sep)])
    return split_path(head) + [tail]


def relative_path(src_path, dst_path=None):
    """Determine relative path between two paths.
    This function is primarily meant for tweaking paths for symlinks.
    Paths ending with '/' are considered as directories.

    @param src_path:
    @type src_path:
    @param: dst_path:
    @type dst_path:
    @returns: relative path from src to dst
    @rtype: str
    """

    if dst_path is None:
        dst_path = os.path.curpath(os.curdir) + "/"
    src_path, src_file = os.path.split(src_path)
    dst_path, dst_file = os.path.split(dst_path)

    src_path = split_path(src_path)
    dst_path = split_path(dst_path)

    if not src_file and dst_file:
        raise RuntimeError("")

    while src_path and dst_path and src_path[0] == dst_path[0]:
        src_path.pop(0)
        dst_path.pop(0)

    while dst_path:
        src_path.insert(0, "..")
        dst_path.pop(0)

    src_path.append(src_file)
    dst_path.append(dst_file)
    return os.path.join(*src_path)


def makedirs(path, mode=0o777):
    """
    Wrapper to os.makedirs which does not
    throw an exception on existing directory.
    """
    try:
        os.makedirs(path, mode)
    except OSError as ex:
        if ex.errno != 17:
            raise
        if not os.path.isdir(path):
            raise
