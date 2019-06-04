# -*- coding: utf-8 -*-


import os
import sys
import signal
import optparse
import logging

# IMPORTANT: import taskd first to set os.environ["PROJECT_DEFAULT_CONFIG_FILE"]
from kobo.worker.taskmanager import TaskManager, TaskContainer

import kobo.conf
import kobo.log
import kobo.process
from kobo.exceptions import ShutdownException
from kobo.tback import Traceback, set_except_hook
set_except_hook()


def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()


def main_loop(conf, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # initialize TaskManager
    try:
        log_file = conf.get("LOG_FILE", None)
        logger = logging.Logger("TaskManager")
        logger.setLevel(logging.DEBUG)
        if log_file:
            log_level = logging.getLevelName(conf.get("LOG_LEVEL", "DEBUG").upper())
            kobo.log.add_rotating_file_logger(logger, log_file, log_level=log_level)

        tm = TaskManager(conf=conf, logger=logger)
    except Exception as ex:
        raise
        sys.stderr.write("Error initializing TaskManager: %s\n" % ex)
        sys.exit(1)

    if foreground and tm._logger is not None:
        kobo.log.add_stderr_logger(tm._logger)

    while 1:
        try:
            tm.log_debug(80 * '-')
            # poll hub for new tasks
            tm.hub._login()
            tm.update_worker_info()
            tm.update_tasks()
            tm.get_next_task()

            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()

            # sleep for some time
            tm.sleep()

        except (ShutdownException, KeyboardInterrupt):
            # ignore keyboard interrupts and sigterm
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            tm.log_info('Exiting...')
            tm.shutdown()
            tm.log_info('Cleanup done...')
            break

        except:
            # this is a little extreme: log the exception and continue
            traceback = Traceback()
            tm.log_error(traceback.get_traceback())
            tm.sleep()


def main(conf, argv=None):
    parser = optparse.OptionParser()
    parser.add_option(
        "-f", "--foreground",
        default=False,
        action="store_true",
        help="run in foreground (do not spawn a daemon)",
    )
    parser.add_option(
        "-k", "--kill",
        default=False,
        action="store_true",
        help="kill the daemon",
    )
    parser.add_option(
        "-p", "--pid-file",
        help="specify a pid file",
    )
    opts, args = parser.parse_args(argv)

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("PID_FILE")

    if pid_file is None:
        parser.error("No pid file specified.")

    if opts.kill:
        pid = open(pid_file, "r").read()
        os.kill(int(pid), 15)
        sys.exit(0)

    if opts.foreground:
        main_loop(conf, foreground=True)
    else:
        kobo.process.daemonize(main_loop, conf=conf, daemon_pid_file=pid_file, foreground=False)
