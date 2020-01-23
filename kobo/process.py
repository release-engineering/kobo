# -*- coding: utf-8 -*-

import os
import re
import io
import sys
import signal
import time


__all__ = (
    "daemonize",
    "get_child_pgids",
    "get_proc_stat",
    "get_process_status",
    "is_success",
    "kill_process_group",
    "kill_group",
)


def daemonize(daemon_func, daemon_pid_file=None, daemon_start_dir="/", daemon_out_log="/dev/null", daemon_err_log="/dev/null", *args, **kwargs):
    """Robustly turn into a UNIX daemon, running in daemon_start_dir."""

    if daemon_pid_file and os.path.exists(daemon_pid_file):
        try:
            f = open(daemon_pid_file, "r")
            pid = f.read()
            f.close()
        except:
            pid = None

        if pid:
            try:
                fn = os.path.join("/proc", pid, "cmdline")
                f = open(fn, "r")
                cmdline = f.read()
                f.close()
            except:
                cmdline = None

            if cmdline and cmdline.find(sys.argv[0]) >= 0:
                sys.stderr.write("A proces is still running, pid: %s\n" % pid)
                sys.exit(1)

    # first fork
    try:
        if os.fork() > 0:
            # exit from first parent
            sys.exit(0)
    except OSError as ex:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (ex.errno, ex.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.setsid()
    try:
        os.chdir(daemon_start_dir)
    except OSError:
        # fallback to "/" (just in case the first chdir fails on insufficient perms or another OSError)
        os.chdir("/")
    os.umask(0)

    # second fork
    try:
        pid = os.fork()
        if pid > 0:
            # write pid to pid_file
            if daemon_pid_file is not None:
                fd = os.open(daemon_pid_file, os.O_WRONLY | os.O_CREAT, 0o644)
                os.write(fd, b"%s" % str(pid).encode())
                os.close(fd)
            # exit from second parent
            sys.exit(0)
    except OSError as ex:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (ex.errno, ex.strerror))
        sys.exit(1)

    # redirect stdin, stdout and stderr
    stdin = open("/dev/null", "r")
    # Python 3
    try:
        stdout = io.TextIOWrapper(open(daemon_out_log, "ab+", 0), write_through=True)
        stderr = io.TextIOWrapper(open(daemon_err_log, "ab+", 0), write_through=True)
    # Python 2
    except TypeError:
        stdout = open(daemon_out_log, "a+", 0)
        stderr = open(daemon_err_log, "a+", 0)
    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    # run the daemon loop
    daemon_func(*args, **kwargs)

#    # delete pid file
#    if daemon_pid_file:
#        try:
#            os.remove(daemon_pid_file)
#        except:
#            pass

    sys.exit(0)


def get_process_status(retval, prefix):
    """Return status description after a process has exited."""

    if type(prefix) in (list, tuple):
        prefix = " ".join(prefix)

    if os.WIFSIGNALED(retval):
        return "%s was killed by signal %i" % (prefix, os.WTERMSIG(retval))
    if os.WIFEXITED(retval):
        return "%s exited with status %i" % (prefix, os.WEXITSTATUS(retval))
    return "%s terminated for unknown reasons" % prefix


def is_success(return_code):
    """Return True if return code indicates successful completion (exited with status 0), False otherwise."""
    if os.WIFEXITED(return_code) and os.WEXITSTATUS(return_code) == 0:
        return True
    return False


procstat_re = re.compile(r"^(?P<pid>-?\d+) \((?P<comm>.+)\) (?P<state>\w) (?P<ppid>-?\d+) (?P<pgid>-?\d+)"
                        +r" (?P<sid>-?\d+) (?P<tty_nr>-?\d+) (?P<tty_pgid>-?\d+) (?P<flags>\d+) (?P<minflt>\d+)"
                        +r" (?P<cminflt>\d+) (?P<majflt>\d+) (?P<cmajflt>\d+) (?P<utime>\d+) (?P<stime>\d+)"
                        +r" (?P<cutime>-?\d+) (?P<cstime>-?\d+) (?P<priority>-?\d+) (?P<nice>-?\d+) (?P<num_threads>\d+)"
                        +r" 0 (?P<itrealvalue>-?\d+) (?P<starttime>-?\d+) (?P<vsize>\d+) (?P<rss>-?\d+)"
                        +r" (?P<startcode>\d+) (?P<endcode>\d+) (?P<startstack>\d+) (?P<kstkesp>\d+) (?P<kstkeip>\d+)"
                        +r" (?P<signal>\d+) (?P<blocked>\d+) (?P<sigignore>\d+) (?P<sigcatch>\d+) (?P<wchan>\d+)"
                        +r" (?P<nswap>\d+) (?P<cnswap>\d+) (?P<exit_signal>-?\d+) (?P<processor>-?\d+) (?P<rt_priority>-?\d+)"
                        +r" (?P<policy>-?\d+) ?(?P<blkio_ticks>\d+)? ?(?P<gtime>\d+) ?(?P<cgtime>-?\d+)?.*$")


def get_proc_stat(pid):
    """Get information from /proc/<PID>/stat.

    See man proc for detail (inaccurate).
    Accurate data can be found in kernel sources: fs/proc/array.c
    """

    # read stat file
    procfile = open("/proc/%s/stat" % pid)
    procdata = procfile.read()
    procfile.close()

    # parse data and store into dictionary
    match = procstat_re.match(procdata)
    if match is not None:
        result = match.groupdict()
        for key in result:
            # keep following field as string
            if key in ("comm", ):
                continue

            # covert rest to integer
            if type(result[key]) is str and result[key].isdigit():
                result[key] = int(result[key])

        return result

    raise IOError("Invalid /proc/%s/stat file" % pid)


def kill_process_group(pid, msg=None, sig=signal.SIGTERM, timeout=5, logger=None):
    """Kill process group with signal, keep trying within timeout.

    Return True if successful, False if not.
    """

    success = True
    for pgid in get_child_pgids(pid)[::-1]:
        # iterate in reverse order so processes whose children are killed might have
        # a chance to cleanup before they"re killed
        success &= kill_group(pgid, msg, sig, timeout, logger)
    return success


# TODO: remove or use *msg* argument
def kill_group(pgid, msg=None, sig=signal.SIGTERM, timeout=5, logger=None):
    """Kill the process group with the given process group ID.
    Return True if the group is successfully killed in the given timeout, False otherwise."""

    incr = 1.0
    t = 0.0

    while t < timeout:
        try:
            pid, retval = os.waitpid(-pgid, os.WNOHANG)
            while pid != 0:
                if logger:
                    logger.info(get_process_status(retval, "kill_group: process %i" % pid))
                pid, retval = os.waitpid(-pgid, os.WNOHANG)
        except OSError as ex:
            # means there are no processes in that process group
            if t == 0.0:
                logger and logger.info("kill_group: Process (pgrp %i) exited" % (pgid))
            else:
                logger and logger.info("kill_group: Killed process (pgrp %i)" % (pgid))
            return True
        else:
            logger and logger.info("kill_group: Process (pgrp %i) exists" % (pgid))

        try:
            os.killpg(pgid, sig)
        except OSError as ex:
            # shouldn't happen
            logger and logger.error("kill_group: Process (pgrp %i): %s" % (pgid, ex))
            continue
        else:
            logger and logger.info("kill_group: Sent signal %i to process (pgrp %i)" % (sig, pgid))

        if t == 0.0:
            time.sleep(0.1)
        else:
            time.sleep(incr)
            t += incr
#        time.sleep(incr)
        t += incr
    logger and logger.error("kill_group: Failed to kill process (pgrp %i)" % (pgid))
    return False


def get_child_pgids(pid):
    """
    Recursively get the children of the process with the given ID.
    Return a list containing the process group IDs of the children
    in depth-first order, without duplicates.
    """

    stats_by_ppid = {}
    pgids = []

    for procdir in os.listdir("/proc"):
        if not procdir.isdigit():
            continue

        try:
            stat = get_proc_stat(procdir)
            stats_by_ppid.setdefault(stat["ppid"], [])
            stats_by_ppid[stat["ppid"]].append(stat)
            if stat["pid"] == pid:
                # put the pgid of the top-level process into the list
                pgids.append(stat["pgid"])
        except (IOError, OSError):
            # We expect IOErrors, because files in /proc may disappear between the listdir() and read().
            # Nothing we can do about it, just move on.
            continue

    if not pgids:
        # assume the pid and pgid of the forked process are the same
        pgids.append(pid)

    pids = [pid]
    while pids:
        for ppid in pids[:]:
            for stat in stats_by_ppid.get(ppid, []):
                # get the /proc entries with ppid as their parent, and append their pgid to the list,
                # then recheck for their children
                if stat["pgid"] not in pgids:
                    pgids.append(stat["pgid"])
                pids.append(stat["pid"])
            pids.remove(ppid)

    return pgids
