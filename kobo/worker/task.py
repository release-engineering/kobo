# -*- coding: utf-8 -*-

from __future__ import print_function

import copy
import signal

from kobo.client.constants import TASK_STATES
from kobo.plugins import Plugin
from kobo.shortcuts import force_list


__all__ = (
    "TaskBase",
    "FailTaskException",
)


class FailTaskException(Exception):
    """Terminate the task."""
    pass


class TaskBase(Plugin):
    """Base class for all tasks."""
    enabled = True

    def __init__(self, hub, conf, task_id, args):
        self._hub = hub  # created by taskmanager
        self._conf = conf
        self._task_id = task_id
        self._task_info = self.hub.worker.get_task(self.task_id)
        self._task_manager = None  # created by taskmanager (only for foreground tasks)
        self._args = args
        self._subtask_list = []
        self.result = ""

    @property
    def hub(self):
        return self._hub

    @property
    def conf(self):
        return self._conf

    @property
    def task_id(self):
        return self._task_id

    @property
    def task_info(self):
        return self._task_info

    def _get_task_manager(self):
        if not getattr(self.__class__, "foreground", False):
            return None
        return self._task_manager

    def _set_task_manager(self, value):
        if not getattr(self.__class__, "foreground", False):
            raise ValueError("Cannot set task_manager for a background task.")
        self._task_manager = value

    task_manager = property(_get_task_manager, _set_task_manager)

    @property
    def args(self):
        # deepcopy to prevent modification
        return copy.deepcopy(self._args)

    @property
    def subtask_list(self):
        # deepcopy to prevent modification
        return copy.deepcopy(self._subtask_list)

    def run(self):
        """Run the task."""
        raise NotImplementedError()

    def fail(self):
        """Fail the task."""
        raise FailTaskException()

    @classmethod
    def cleanup(cls, hub, conf, task_info):
        pass

    @classmethod
    def notification(cls, hub, conf, task_info):
        pass

    def spawn_subtask(self, method, args, label=""):
        """Spawn a new subtask."""
        if self.foreground:
            raise RuntimeError("Foreground tasks can't spawn subtasks.")

        subtask_id = self.hub.worker.create_subtask(label, method, args, self.task_id)
        self._subtask_list.append(subtask_id)
        return subtask_id

    def wait(self, subtasks=None):
        """Wait until subtasks finish.

        subtasks = None - wait for all subtasks
        subtasks = [task_id list] - wait for selected subtasks
        """

        if self.foreground:
            # wait would call signal.pause() in the *main* worker thread and lock program forever
            raise RuntimeError("Foreground tasks can't wait on subtasks.")

        if subtasks is not None:
            subtasks = force_list(subtasks)

        self.hub.worker.wait(self.task_id, subtasks)

        finished = []
        while True:
            (finished, unfinished) = self.hub.worker.check_wait(self.task_id)

            if not unfinished:
                # all done
                break

            # sleep
            signal.pause()
            # wake up on signal to check the status

        # remove finished subtasks from the list, check results
        fail = False
        for i in finished:
            state = self.hub.worker.get_task(i)
            if state['state'] != TASK_STATES['CLOSED']:
                fail = True
            self._subtask_list.remove(i)

        if fail:
            print("Failing because of at least one subtask hasn't closed properly.")
            self.fail()

        return finished
