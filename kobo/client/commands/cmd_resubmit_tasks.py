# -*- coding: utf-8 -*-


import sys

from kobo.client.task_watcher import *
from kobo.client import ClientCommand


class Resubmit_Tasks(ClientCommand):
    """resubmit failed tasks"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s task_id [task_id...]" % self.normalized_name


    def run(self, *args, **kwargs):
        if len(args) == 0:
            self.parser.error("At least one task id must be specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        tasks = args

        self.set_hub(username, password)
        resubmitted_tasks = []
        failed = False
        for task_id in tasks:
            try:
                resubmitted_id = self.hub.client.resubmit_task(task_id)
                resubmitted_tasks.append(resubmitted_id)
            except Exception, ex:
                failed = True
                print ex

        TaskWatcher.watch_tasks(self.hub, resubmitted_tasks)
        if failed:
            sys.exit(1)
