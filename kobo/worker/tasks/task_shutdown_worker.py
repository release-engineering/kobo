# -*- coding: utf-8 -*-

from kobo.worker import TaskBase
from kobo.exceptions import ShutdownException


class ShutdownWorker(TaskBase):
    enabled = True

    arches = ["noarch"]
    channels = ["default"]
    exclusive = True
    foreground = True
    priority = 19
    weight = 0.0

    def run(self):
        kill = self.args.get("kill", False)

        if kill:
            # raise exception and terminate immediately
            raise ShutdownException()

        # lock the task manager and let it terminate all tasks
        self.task_manager.locked = True
