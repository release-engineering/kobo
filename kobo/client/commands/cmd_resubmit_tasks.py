# -*- coding: utf-8 -*-


from __future__ import print_function
import sys

from kobo.client.task_watcher import TaskWatcher
from kobo.client import ClientCommand


class Resubmit_Tasks(ClientCommand):
    """resubmit failed tasks"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s task_id [task_id...]" % self.normalized_name
        self.parser.add_option("--force", action="store_true", help="Resubmit also tasks which are closed properly.")
        self.parser.add_option("--nowait", default=False, action="store_true", help="Don't wait until tasks finish.")
        self.parser.add_option("--priority", help="priority")


    def run(self, *args, **kwargs):
        if len(args) == 0:
            self.parser.error("At least one task id must be specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        force = kwargs.pop("force", False)
        priority = kwargs.pop("priority", None)

        tasks = args

        self.set_hub(username, password)
        resubmitted_tasks = []
        failed = False
        for task_id in tasks:
            try:
                resubmitted_id = self.hub.client.resubmit_task(task_id, force, *[arg for arg in [priority] if arg is not None])
                resubmitted_tasks.append(resubmitted_id)
            except Exception as ex:
                failed = True
                print(ex)

        if not kwargs.get('nowait'):
            TaskWatcher.watch_tasks(self.hub, resubmitted_tasks)
        if failed:
            sys.exit(1)
