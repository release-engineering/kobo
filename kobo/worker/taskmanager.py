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
import signal
import time
import datetime
from xmlrpclib import Fault, ProtocolError
from cStringIO import StringIO

import kobo.conf
import kobo.worker.logger
import kobo.log
import kobo.tback
from kobo.client import HubProxy
from kobo.exceptions import ShutdownException

from kobo.process import kill_process_group, get_process_status
from kobo.plugins import PluginContainer

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


class TaskManager(kobo.log.LoggingBase):
    """Task manager takes and executes new tasks."""

    __slots__ = (
        "hub",         	            # xml-rpc hub client
        "conf",
        "task_container",
        "worker_info",              # worker information obtained from hub
        "pid_dict",                 # { task_id: pid }
        "task_dict",                # { task_id: { task information obtained from self.hub.get_worker_tasks() } }
        "locked",                   # if task manager is locked, it waits until tasks finish and exits
        # TODO: last seen attribute?
    )


    def __init__(self, conf, logger=None, **kwargs):
        kobo.log.LoggingBase.__init__(self, logger)
        self.conf = kobo.conf.PyConfigParser()

        # load default config
        default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
        self.conf.load_from_file(default_config)

        # update data from another config
        if conf is not None:
            self.conf.load_from_conf(conf)

        # update data from kwargs
        self.conf.load_from_dict(kwargs)

        self.pid_dict = {}
        self.task_dict = {}

        self.locked = False

        self.task_container = TaskContainer()

        # self.hub is created here
        self.hub = HubProxy(conf, client_type="worker", logger=self._logger, **kwargs)
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

        self.log_debug("Updating worker info.")
        try:
            self.worker_info = self.hub.worker.update_worker(self.worker_info["enabled"], self.worker_info["ready"], len(self.pid_dict))
        except ProtocolError, ex:
            self.log_error("Cannot update worker info: %s" % ex)
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
                self.log_error("Cannot wake up task %s: %s" % (self._task_str(task_info), ex))
            else:
                self.log_info("Waking up task %s." % self._task_str(task_info))


    def update_tasks(self):
        """Read and process task statuses from hub.

        The processing we do is:
          1. clean up after tasks that are not longer active
          2. wake waiting tasks if appropriate
        """

        task_list = {}
        interrupted_list = []
        timeout_list = []
        finished_tasks = set()

        for task_info in self.hub.worker.get_worker_tasks():
            self.log_debug("Checking task: %s." % self._task_str(task_info))

            if task_info["state"] == TASK_STATES["OPEN"] and task_info["id"] not in self.pid_dict:
                # an interrupted task appears to be open, but running task manager doesn't track it in it's pid list
                # this happens after a power outage, for example
                interrupted_list.append(task_info["id"])
                finished_tasks.add(task_info["id"])
                continue

            if task_info["timeout"] is not None:
                time_delta = datetime.datetime.now() - datetime.datetime(*time.strptime(task_info["dt_started"], "%Y-%m-%d %H:%M:%S")[0:6])
                #time_delta = datetime.datetime.now() - datetime.datetime.strptime(task_info["dt_started"], "%Y-%m-%d %H:%M:%S") #for Python2.5+
                if time_delta.seconds >= (int(task_info["timeout"])):
                    timeout_list.append(task_info["id"])
                    finished_tasks.add(task_info["id"])
                    continue

            task_list[task_info["id"]] = task_info
            self.wakeup_task(task_info)

        self.task_dict = task_list
        self.log_debug("Current tasks: %r" % self.task_dict.keys())

        if interrupted_list:
            self.log_warning("Closing interrupted tasks: %r" % sorted(interrupted_list))
            try:
                self.hub.worker.interrupt_tasks(interrupted_list)
            except (ShutdownException, KeyboardInterrupt):
                raise
            except Exception, ex:
                self.log_error("%s" % ex)

        if timeout_list:
            self.log_warning("Closing timed out tasks: %r" % sorted(timeout_list))
            try:
                self.hub.worker.timeout_tasks(timeout_list)
            except (ShutdownException, KeyboardInterrupt):
                raise
            except Exception, ex:
                self.log_error("%s" % ex)

        self.log_debug("pids: %s" % self.pid_dict.values())
        for task_id in self.pid_dict.keys():
            if self.is_finished_task(task_id):
                self.log_info("Task has finished: %s" % task_id)
                finished_tasks.add(task_id)
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
                        self.log_info("Killing canceled task %r (pid %r)" % (task_id, pid))
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                            finished_tasks.add(task_id)
                    if task["state"] == TASK_STATES["TIMEOUT"]:
                        self.log_info("Killing timed out task %r (pid %r)" % (task_id, pid))
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                            finished_tasks.add(task_id)
                    elif "worker_id" in task and task["worker_id"] != self.worker_info["id"]:
                        self.log_info("Killing reassigned task %r (pid %r)" % (task_id, pid))
                        # TODO: Task.cleanup() - be careful, cleanup may remove running task's data!
                        if self.cleanup_task(task_id):
                            del self.pid_dict[task_id]
                    else:
                        self.log_warning("Lingering task %r (pid %r)" % (task_id, pid))
                except (ShutdownException, KeyboardInterrupt):
                    raise
                except Exception:
                    # TODO: do not catch generic error
                    self.log_error("Invalid task %r (pid %r)" % (task_id, pid))
                    raise

        for task_id in sorted(finished_tasks):
            task_info = self.hub.worker.get_task(task_id)
            self.finish_task(task_info)

        self.update_worker_info()


    def get_next_task(self):
        """ """
        if not self.worker_info["enabled"]:
            self.log_info("Worker is disabled.")
            return

        if not self.worker_info["ready"]:
            self.log_info("Worker is not ready to take another task.")
            return

        if self.locked:
            task_list = self.hub.worker.get_worker_tasks()
            if len(task_list) == 0:
                raise ShutdownException()

            awaited_task_list = self.hub.worker.get_awaited_tasks(task_list)
            self.log_debug("Current awaited tasks: %r" % [ task_info["id"] for task_info in awaited_task_list ])

            # process assigned tasks first
            for task_info in awaited_task_list:
                self.take_task(task_info)

            return

        assigned_task_list = self.hub.worker.get_tasks_to_assign()
        self.log_debug("Current assigned tasks: %r" % [ task_info["id"] for task_info in assigned_task_list ])

        # process assigned tasks first
        for task_info in assigned_task_list:
            self.take_task(task_info)


    def take_task(self, task_info):
        """Attempt to open the specified task. Return True on success, False otherwise."""

        if not self.worker_info["ready"]:
            return

        try:
            TaskClass = self.task_container[task_info["method"]]
        except (KeyError, ValueError):
            self.log_error("Cannot take unknown task %s (#%s)" % (task_info["method"], task_info["id"]))
            time.sleep(1) # prevent log flooding
            return

        if not TaskClass.exclusive:
            # always process exclusive tasks, regardless architecture or channel
            if task_info["arch"]["name"] not in TaskClass.arches:
                self.log_error("Unsupported arch for task %s: %s" % (self._task_str(task_info), task_info["arch"]["name"]))
                return

            if task_info["channel"]["name"] not in TaskClass.channels:
                self.log_error("Unsupported channel for task %s: %s)" % (self._task_str(task_info), task_info["channel"]["name"]))
                return

        self.log_info("Attempting to take task %s" % self._task_str(task_info))

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
            self.log_error("Cannot open task %s: %s" % (self._task_str(task_info), reason))
            return

        self.worker_info["current_load"] += TaskClass.weight
        self.worker_info["ready"] = self.worker_info["current_load"] < self.worker_info["max_load"]

        if TaskClass.foreground:
            self.run_task(task_info)
            self.finish_task(task_info)
        else:
            pid = self.fork_task(task_info)
            self.pid_dict[task_info["id"]] = pid


    def fork_task(self, task_info):
        self.log_debug("Forking task %s" % self._task_str(task_info))

        pid = os.fork()
        if pid:
            self.log_info("Task forked %s: pid=%s" % (self._task_str(task_info), pid))
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
        TaskClass = self.task_container[task_info["method"]]

        # add *task_manager* attribute to foreground tasks
        if TaskClass.foreground:
            # TODO:
            TaskClass.task_manager = self
            hub = self.hub
        else:
            # create a new session for the task
            hub = HubProxy(self.conf, client_type="worker")

        task = TaskClass(hub, self.conf, task_info["id"], task_info["args"])

        # redirect stdout and stderr
        thread = kobo.worker.logger.LoggingThread(hub, task_info["id"])
        sys.stdout = kobo.worker.logger.LoggingIO(open(os.devnull, "w"), thread)
        sys.stderr = sys.stdout
        thread.start()

        failed = False
        try:
            task.run()
        except ShutdownException:
            thread.stop()
            if TaskClass.foreground and TaskClass.exclusive:
                # close task (shutdown-worker and similar control tasks) and raise
                hub.worker.close_task(task.task_id, task.result)
                raise
            # interrupt otherwise
            hub.worker.interrupt_tasks([task.task_id])
            return
        except KeyboardInterrupt:
            thread.stop()
            # interrupt otherwise
            hub.worker.interrupt_tasks([task.task_id])
            return
        except SystemExit, ex:
            if len(ex.args) > 0 and ex.args[0] != 0:
                sys.stdout.write("\nProgram has exited with return code '%s'." % ex.args[0])
                failed = True
        except FailTaskException, ex:
            failed = True
        except:
            message = "ERROR: %s\n" % kobo.tback.get_exception()
            message += "See traceback.log for details (admin only).\n"
            hub.upload_task_log(StringIO(message), task.task_id, "error.log")
            hub.upload_task_log(StringIO(kobo.tback.Traceback().get_traceback()), task.task_id, "traceback.log", mode=0600)
            failed = True

        thread.stop()
        if failed:
            hub.worker.fail_task(task.task_id, task.result)
        else:
            hub.worker.close_task(task.task_id, task.result)


    def finish_task(self, task_info):
        TaskClass = self.task_container[task_info["method"]]
        try:
            TaskClass.cleanup(self.hub, self.conf, task_info)
        except:
            self.log_critical(kobo.tback.get_exception())
        try:
            TaskClass.notification(self.hub, self.conf, task_info)
        except:
            self.log_critical(kobo.tback.get_exception())


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
                self.log_error("Process hasn't exited with errno.ECHILD: %s" % task_id)
                raise

            # the process is already gone
            return False

        if childpid != 0:
            prefix = "Task #%s" % task_id
            self.log_info(get_process_status(status, prefix))
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
            success = kill_process_group(self.pid_dict[task_id], logger=self._logger)
        except IOError, ex:
            # proc file doesn"t exist -> process was already killed
            success = True

        if not success:
#            self.logger.debug("cleanup_task: Trying to terminate task with SIGKILL: %s [#%s] (pid: %s)" % (self.task_dict[task_id]["method"], task_id, self.pid_dict[task_id]))
            try:
#                success = kill_process_group(self.pid_dict[task_id], signal.SIGKILL, timeout=2)
                success = kill_process_group(self.pid_dict[task_id], signal.SIGKILL, timeout=2, logger=self._logger)
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
        self.log_info("Locking...")
