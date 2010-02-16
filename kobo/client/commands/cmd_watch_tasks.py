# -*- coding: utf-8 -*-


from kobo.client.task_watcher import *
from kobo.client import ClientCommand


class Watch_Tasks(ClientCommand):
    """track progress of particular tasks"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s task_id [task_id...]" % self.normalized_name


    def run(self, *args, **kwargs):
        if len(args) == 0:
            self.parser.error("At least one task id must be specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        self.set_hub(username, password)
        TaskWatcher.watch_tasks(self.hub, args)
