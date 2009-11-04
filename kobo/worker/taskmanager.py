# -*- coding: utf-8 -*-


"""

Struct: worker_info
=================
>>> worker_info = {
        "id": int,
        "name": str,
        "arches": dict,
        "channels": dict,
        "enabled": bool,
        "max_load": bool,
        "ready": bool,
        "task_count": int,
        "current_load": float,
        "hub_version": str,
    }

Struct: task_info
=================
>>> task_info = {
        "id": int,
        "worker_id": int or None,
        "worker": worker_info or None,
        "parent": task_info or None,
        "state": str,
        "label": str,
        "method": str,
        "args": dict,
        "result": str,
        "traceback": str,
        "exclusive": bool,
        "arch": dict,
        "channel": dict,
        "timeout": int,
        "waiting": bool,
        "awaited": bool,
        "dt_created": datetime,
        "dt_started": datetime or None,
        "dt_finished": datetime or None,
        "priority": int,
        "weight": int,
    }
"""


import errno
import os
import sys
import logging
import signal
import time
import datetime
import Queue
import threading
from xmlrpclib import Fault, ProtocolError
from cStringIO import StringIO

import kobo.conf
from kobo.client import HubProxy
from kobo.exceptions import ShutdownException

from kobo.process import kill_process_group, get_process_status
from kobo.tback import Traceback
from kobo.log import add_rotating_file_logger
from kobo.plugins import PluginContainer
from kobo.conf import settings

from task import FailTaskException
from kobo.client.constants import TASK_STATES


__all__ = (
    "TaskContainer",
    "TaskManager",
    "Fault",
    "ProtocolError",
    "ShutdownException",
)


# tasks are registered in __init__.py
class TaskContainer(PluginContainer):
    """Task container."""
    pass


class TaskManager(object):
    """Task manager takes and executes new tasks."""

    __slots__ = (
        "hub",         	            # xml-rpc hub client
        "conf",
        "logger",
        "task_container",
        "worker_info",              # worker information obtained from hub
        "pid_dict",                 # { task_id: pid }
        "task_dict",                # { task_id: { task information obtained from self.hub.get_worker_tasks() } }
        "locked",                   # if task manager is locked, it waits until tasks finish and exits
        # TODO: last seen attribute?
    )


    def __init__(self, logger=None, conf=None, **kwargs):
        self.conf = kobo.conf.PyConfigParser()

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self.conf.load_from_file(default_config)

        # update data from another config
        if conf is not None:
            self.conf.load_from_conf(conf)

        # update data from config specified in os.environ
        conf_environ_key = "TASK_MANAGER_CONFIG_FILE"
        if conf_environ_key in os.environ:
            self.conf.load_from_file(os.environ[conf_environ_key])

        # update data from kwargs
        self.conf.load_from_dict(kwargs)

        # setup logger
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger("TaskManager")
            self.logger.setLevel(logging.DEBUG)
            log_level = logging._levelNames.get(self.conf["LOG_LEVEL"].upper())
            log_file = self.conf["LOG_FILE"]
            add_rotating_file_logger(self.logger, log_file, log_level=log_level)

        self.pid_dict = {}
        self.task_dict = {}

        self.locked = False

        self.task_container = TaskContainer()

        # self.hub is created here
        self.hub = HubProxy(client_type="worker", logger=self.logger, conf=self.conf, **kwargs)
        self.worker_info = self.hub.worker.get_worker_info()
        self.update_worker_info()


    def _task_str(self, task_info):
        """Return a task description."""
        return "#%s [%s]" % (task_info["id"], task_info["method"])


    def sleep(self):
        """Sleep between polls."""
        time.sleep(self.conf.get("SLEEP_TIME", 20))


    def update_worker_info(self):
        """Update worker_info dictionary."""

        self.logger.debug("Updating worker info.")
        try:
            self.worker_info = self.hub.worker.update_worker(self.worker_info["enabled"], self.worker_info["ready"], len(self.pid_dict))
        except ProtocolError, ex:
            self.logger.error("Cannot update worker info: %s" % ex)
            return


#    def check_version(self):
#        """Check if worker version matches with hub."""
#        hub_version = self.worker_info.get("hub_version", None)
#        if hub_version is not None and not self.locked:
#            if str(self.version) != str(hub_version):
#                self.logger.error("Invalid version detected [worker=%s, hub=%s]." % (self.version, hub_version))
#                self.lock()


    def wakeup_task(self, task_info):
        # alert is set in hub.worker.get_worker_tasks() when the task is supposed to wake up
        if task_info.get("alert", False):
            try:
                os.kill(self.pid_dict[task_info["id"]], signal.SIGUSR2)
            except OSError, ex:
                self.logger.error("Cannot wake up task %s: %s" % (self._task_str(task_info), ex))
            else:
                self.logger.info("Waking up task %s." % self._task_str(task_info))


    def update_tasks(self):
        """Read and process task statuses from hub.

        The processing we do is:
          1. clean up after tasks that are not longer active
          2. wake waiting tasks if appropriate
        """

        task_list = {}
        interrupted_list = []
        timeout_list = []

        for task_info in self.hub.worker.get_worker_tasks():
            self.logger.debug("Checking task: %s." % self._task_str(task_info))

            if task_info["state"] == TASK_STATES["OPEN"] and task_info["id"] not in self.pid_dict:
                # an interrupted task appears to be open, but running task manager doesn't track it in it's pid list
                # this happens after a power outage, for example
                interrupted_list.append(task_info["id"])
                continue

            if task_info["timeout"] is not None:
                time_delta = datetime.datetime.now() - datetime.datetime(*time.strptime(task_info["dt_started"], "%Y-%m-%d %H:%M:%S")[0:6])
                #time_delta = datetime.datetime.now() - datetime.datetime.strptime(task_info["dt_started"], "%Y-%m-%d %H:%M:%S") #for Python2.5+
                if time_delta.seconds >= (int(task_info["timeout"])):
                    timeout_list.append(task_info["id"])
                    continue

            task_list[task_info["id"]] = task_info

        self.task_dict = task_list
        self.logger.debug("Current tasks: %r" % self.task_dict.keys())

        if interrupted_list:
            self.logger.warning("Closing interrupted tasks: %r" % sorted(interrupted_list))
            try:
                self.hub.worker.interrupt_tasks(interrupted_list)
            except (ShutdownException, KeyboardInterrupt):
                raise
            except Exception, ex:
                self.logger.error("%s" % ex)

        if timeout_list:
            self.logger.warning("Closing timed out tasks: %r" % sorted(timeout_list))
            try:
                self.hub.worker.timeout_tasks(timeout_list)
            except (ShutdownException, KeyboardInterrupt):
                raise
            except Exception, ex:
                self.logger.error("%s" % ex)

        self.logger.debug("pids: %s" % self.pid_dict.values())
        for task_id in self.pid_dict.keys():
            if self.is_finished_task(task_id):
                self.logger.info("Task has finished: %s" % task_id)
                # the subprocess handles most everything, we just need to clear things out
                if self.cleanup_task(task_id):
                    del self.pid_dict[task_id]
                if task_id in self.task_dict:
                    del self.task_dict[task_id]

        for task_id, pid in self.pid_dict.items():
            if task_id not in self.task_dict:
                # expected to happen when:
                #  - we are in the narrow gap between the time the task records its result
                #    and the time the process actually exits.
                #  - task is canceled
                #  - task is forcibly reassigned/unassigned

                try:
                    task = self.hub.worker.get_task_no_verify(task_id)
                    if task["state"] == TASK_STATES["CANCELED"]:
                        self.logger.info("Killing canceled task %r (pid %r)" % (task_id, pid))
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                    if task["state"] == TASK_STATES["TIMEOUT"]:
                        self.logger.info("Killing timed out task %r (pid %r)" % (task_id, pid))
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                    elif "worker_id" in task and task["worker_id"] != self.worker_info["id"]:
                        self.logger.info("Killing reassigned task %r (pid %r)" % (task_id, pid))
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                    else:
                        self.logger.warning("Lingering task %r (pid %r)" % (task_id, pid))
                except (ShutdownException, KeyboardInterrupt):
                    raise
                except Exception:
                    # TODO: do not catch generic error
                    self.logger.error("Invalid task %r (pid %r)" % (task_id, pid))
                    raise

        self.update_worker_info()


    def get_next_task(self):
        """ """
        if not self.worker_info["enabled"]:
            self.logger.info("Worker is disabled.")
            return

        if not self.worker_info["ready"]:
            self.logger.info("Worker is not ready to take another task.")
            return

        if self.locked:
            task_list = self.hub.worker.get_worker_tasks()
            if len(task_list) == 0:
                raise ShutdownException()

            awaited_task_list = self.hub.worker.get_awaited_tasks(task_list)
            self.logger.debug("Current awaited tasks: %r" % [ task_info["id"] for task_info in awaited_task_list ])

            # process assigned tasks first
            for task_info in awaited_task_list:
                self.take_task(task_info)

            return

        assigned_task_list = self.hub.worker.get_tasks_to_assign()
        self.logger.debug("Current assigned tasks: %r" % [ task_info["id"] for task_info in assigned_task_list ])

        # process assigned tasks first
        for task_info in assigned_task_list:
            self.take_task(task_info)


    def take_task(self, task_info):
        """Attempt to open the specified task. Return True on success, False otherwise."""

        if not self.worker_info["ready"]:
            return

        try:
            TaskClass = self.task_container[task_info["method"]]
        except (AttributeError, ValueError):
            self.logger.error("Cannot take unknown task %s" % (task_info["method"], task_info["id"]))
            time.sleep(1) # prevent log flooding
            return

        if not TaskClass.exclusive:
            # always process exclusive tasks, regardless architecture or channel
            if task_info["arch"]["name"] not in TaskClass.arches:
                self.logger.error("Unsupported arch for task %s: %s" % (self._task_str(task_info), task_info["arch"]["name"]))
                return

            if task_info["channel"]["name"] not in TaskClass.channels:
                self.logger.error("Unsupported channel for task %s: %s)" % (self._task_str(task_info), task_info["channel"]["name"]))
                return

        self.logger.info("Attempting to take task %s" % self._task_str(task_info))

        # TODO: improve exception handling and logging
        result = False
        reason = ""
        if task_info["state"] in (TASK_STATES["FREE"], TASK_STATES["ASSIGNED"]):
            try:
                # skip the "assign" step and try to open directly
                self.hub.worker.open_task(task_info["id"])
                result = True
            except (ShutdownException, KeyboardInterrupt):
                raise
            except Fault, ex:
                reason = "[%s] %s" % (ex.faultCode, ex.faultString)
            except Exception, ex:
                # TODO: log proper error message
#                self.logger.error("[%s] %s" % (ex.faultCode, ex.faultString))
                reason = "%s" % ex

        if not result:
            self.logger.error("Cannot open task %s: %s" % (self._task_str(task_info), reason))
            return

        self.worker_info["current_load"] += TaskClass.weight
        self.worker_info["ready"] = self.worker_info["current_load"] < self.worker_info["max_load"]

        if TaskClass.foreground:
            self.run_task(task_info)
        else:
            pid = self.fork_task(task_info)
            self.pid_dict[task_info["id"]] = pid


    def fork_task(self, task_info):
        self.logger.debug("Forking task %s" % self._task_str(task_info))

        pid = os.fork()
        if pid:
            self.logger.info("Task forked %s: pid=%s" % (self._task_str(task_info), pid))
            return pid

        # in no circumstance should we return after the fork
        # nor should any exceptions propagate past here
        try:
            # set process group
            os.setpgrp()

            # set a do-nothing handler for sigusr2
            # do not use signal.signal(signal.SIGUSR2, signal.SIG_IGN) - it completely masks interrups !!!
            signal.signal(signal.SIGUSR2, lambda *args: None)

            # set a default handler for SIGTERM
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

            # run the task
            self.run_task(task_info)
        finally:
            # die
            os._exit(os.EX_OK)


    def run_task(self, task_info):
        def get_stdout():
            sys.stdout.seek(0)
            return sys.stdout.read()

        TaskClass = self.task_container[task_info["method"]]

        # add *task_manager* attribute to foreground tasks
        if TaskClass.foreground:
            # TODO:
            TaskClass.task_manager = self
            hub = self.hub
        else:
            # create a new session for the task
            hub = HubProxy(client_type="worker", conf=settings)

        task = TaskClass(hub, task_info["id"], task_info["args"])



        # redirect stdout and stderr
        sys.stdout = LoggingStringIO()
        sys.stderr = sys.stdout
        thread = LoggingThread(hub, task_info["id"], sys.stdout._queue)
        thread.start()

        try:
            task.run()
        except (Exception, SystemExit), outer_ex:
            thread.terminate = True
            thread.join()
            try:
                raise outer_ex
            except (ShutdownException, KeyboardInterrupt):
                if TaskClass.exclusive and TaskClass.foreground:
                    self.hub.worker.close_task(task.task_id, "")
                raise
            except SystemExit, ex:
                if len(ex.args) == 0 or ex.args[0] == 0:
                    self.hub.worker.close_task(task.task_id, get_stdout())
                else:
                    sys.stdout.write("\nProgram has exited with return code '%s'." % ex.args[0])
                    self.hub.worker.fail_task(task.task_id, get_stdout())
            except FailTaskException, ex:
                self.hub.worker.fail_task(task.task_id, get_stdout())
            except Exception:
                traceback = Traceback()
                self.hub.worker.fail_task(task.task_id, get_stdout(), traceback.get_traceback())
        else:
            thread.terminate = True
            thread.join()
            self.hub.worker.close_task(task.task_id, get_stdout())


    def is_finished_task(self, task_id):
        """Determine if task has finished.
        Calling os.waitpid removes finished child process zombies.
        """
        pid = self.pid_dict[task_id]

        try:
            (childpid, status) = os.waitpid(pid, os.WNOHANG)
        except OSError, ex:
            if ex.errno != errno.ECHILD:
                # should not happen
                self.logger.error("Process hasn't exited with errno.ECHILD: %s" % task_id)
                raise

            # the process is already gone
            return False

        if childpid != 0:
            prefix = "Task #%s" % task_id
            self.logger.info(get_process_status(status, prefix))
            return True

        return False


    def cleanup_task(self, task_id):
        """Cleanup after the task.
          - kill child processes
        """

        # clean up stray subtasks
#        self.logger.debug("cleanup_task: Trying to terminate task with SIGTERM: %s [#%s] (pid: %s)" % (self.task_dict[task_id]["method"], task_id, self.pid_dict[task_id]))

        try:
#            success = kill_process_group(self.pid_dict[task_id])
            success = kill_process_group(self.pid_dict[task_id], logger=self.logger)
        except IOError, ex:
            # proc file doesn"t exist -> process was already killed
            success = True

        if not success:
#            self.logger.debug("cleanup_task: Trying to terminate task with SIGKILL: %s [#%s] (pid: %s)" % (self.task_dict[task_id]["method"], task_id, self.pid_dict[task_id]))
            try:
#                success = kill_process_group(self.pid_dict[task_id], signal.SIGKILL, timeout=2)
                success = kill_process_group(self.pid_dict[task_id], signal.SIGKILL, timeout=2, logger=self.logger)
            except IOError:
                # proc file doesn"t exist -> process was already killed
                success = True

#        if success:
#            self.logger.info("cleanup_task: Task terminated: %s [#%s] (pid: %s)" % (self.task_dict[task_id]["method"], task_id, self.pid_dict[task_id]))
#        else:
#            self.logger.error("cleanup_task: Task NOT terminated: %s [#%s] (pid: %s)" % (self.task_dict[task_id]["method"], task_id, self.pid_dict[task_id]))

        return success


    def shutdown(self):
        """Terminate all tasks and exit."""
        for task_id, task_info in self.task_dict.iteritems():
            try:
                TaskClass = self.task_container[task_info["method"]]
            except (AttributeError, ValueError):
                # unknown TaskClass -> skip it
                continue

            if not TaskClass.foreground:
                self.cleanup_task(task_id)

        if self.task_dict:
            # interrupt only if there are some tasks to interrupt
            self.hub.worker.interrupt_tasks(self.task_dict.keys())
        self.update_worker_info()


    def lock(self):
        """Lock the task manager to finish all assigned tasks and exit."""
        self.locked = True
        self.logger.info("Locking...")


class LoggingThread(threading.Thread):
    """Send stdout data to hub in a background thread."""
    __slots__ = (
        "hub",
        "task_id",
        "queue",
        "terminate",
        "last_sent",
        "data_to_send",
    )


    def __init__(self, hub, task_id, queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.hub = hub
        self.task_id = task_id
        self.queue = queue
        self.terminate = False
        self.last_sent = datetime.datetime.now()
        self.data_to_send = ""


    def _has_data_to_send(self, force):
        if force:
            return True
        if self.data_to_send:
            return True
        if self.queue.qsize() > 500:
            return True
        if not self.queue.empty() and (datetime.datetime.now() > self.last_sent + datetime.timedelta(seconds=1)):
            return True
        return False


    def send(self, force=False):
        if self._has_data_to_send(force):
            while True:
                try:
                    self.data_to_send += self.queue.get(block=False)
                except Queue.Empty:
                    break

            if not self.data_to_send:
                return

            try:
                self.hub.upload_task_log(StringIO(self.data_to_send), self.task_id, "stdout.log", append=True)
            except Fault:
                from kobo.tback import Traceback
                open("/tmp/log_fault", "w").write(Traceback().get_traceback())

                # send failed, keep data for the next send() call
                pass
            else:
                self.data_to_send = ""


    def finish(self):
        for i in xrange(3):
            if self.send(force=True):
                return True
            time.sleep(1)
        return False


    def run(self):
        try:
            while not self.terminate:
                time.sleep(1)
                self.send()
            self.finish()
        except:
            from kobo.tback import Traceback
            open("/tmp/log", "w").write(Traceback().get_traceback())


class LoggingStringIO(object):
    """StringIO wrapper also appends all written data to a Queue."""
    __slots__ = (
        "_stringio",
        "_queue",
    )


    def __init__(self, *args, **kwargs):
        self._stringio = StringIO(*args, **kwargs)
        self._queue = Queue.Queue()


    def write(self, buff):
        self._queue.put(buff)
        return self._stringio.write(buff)


    def __getattr__(self, name):
        return getattr(self._stringio, name)
