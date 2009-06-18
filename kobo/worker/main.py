# -*- coding: utf-8 -*-


import os
import sys
import signal
from optparse import OptionParser

# IMPORTANT: import taskd first to set os.environ["PROJECT_DEFAULT_CONFIG_FILE"]
from kobo.worker.taskmanager import TaskManager, TaskContainer

from kobo.conf import settings
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger
set_except_hook()


def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()


def main_loop(foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # initialize TaskManager
    try:
        tm = TaskManager()
    except Exception, ex:
        sys.stderr.write("Error initializing TaskManager: %s\n" % ex)
        sys.exit(1)

    if foreground:
        add_stderr_logger(tm.logger)

    while 1:
        try:
            tm.logger.debug(80 * '-')
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

            tm.logger.info('Exiting...')
            tm.shutdown()
            tm.logger.info('Cleanup done...')
            break

        except:
            # this is a little extreme: log the exception and continue
            traceback = Traceback()
            tm.logger.error(traceback.get_traceback())
            tm.sleep()


def main():
    parser = OptionParser()
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-k", "--kill", default=False, action="store_true",
                      help="kill the daemon")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    (opts, args) = parser.parse_args()

    # TODO: improve a bit, pid is read/written in too many different places
    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = settings.get("PID_FILE", "/var/run/kobo-worker.pid")

    if opts.kill:
        pid = open(pid_file, "r").read()
        os.kill(int(pid), 15)
        sys.exit(0)

    if opts.foreground:
        main_loop(foreground=True)
    else:
        daemonize(main_loop, daemon_pid_file=pid_file, foreground=False)
