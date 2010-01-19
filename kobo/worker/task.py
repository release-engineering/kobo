# -*- coding: utf-8 -*-


import copy
import signal

from kobo.plugins import Plugin
from kobo.shortcuts import force_list
from kobo.client.constants import TASK_STATES


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

    __slots__ = (
        # reserved for class attributes
        "arches",
        "channels",
        "exclusive",
        "foreground",
        "priority",
        "weight",

        "_hub",
        "_task_id",
        "_task_info",
        "_task_manager",
        "_subtask_list",
        "_args",
    )


    def __init__(self, hub, task_id, args):
        self._hub = hub            # created by taskmanager
        self._task_id = task_id
        self._task_info = self.hub.worker.get_task(self.task_id)
        self._task_manager = None  # created by taskmanager (only for foreground tasks)
        self._args = args
        self._subtask_list = []


    @property
    def hub(self):
        return self._hub


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


    def spawn_subtask(self, method, args, label=""):
        """Spawn a new subtask."""
        subtask_id = self.hub.worker.create_subtask(label, method, args, self.task_id)
        self._subtask_list.append(subtask_id)
        return subtask_id


    def wait(self, subtasks=None):
        """Wait until subtasks finish.

        subtasks = None - wait for all subtasks
        subtasks = [task_id list] - wait for selected subtasks
        """

        if subtasks is not None:
            subtasks = force_list(subtasks)

        self.hub.worker.wait(self.task_id, subtasks)

        finished = []
        while True:
            (finished, unfinished) = self.hub.worker.check_wait(self.task_id)

            if len(unfinished) == 0:
                # all done
                break

            # sleep
            signal.pause()
            # wake up on signal to check the status

        # remove finished subtasks from the list, check results
        fail = False
        for i in finished:
            state = self.hub.worker.get_task(i)
            if state != TASK_STATES['CLOSED']:
                fail = True
            self._subtask_list.remove(i)

        if fail:
            print "Failing because of at least one subtask hasn't closed properly."
            self.fail()

        return finished
