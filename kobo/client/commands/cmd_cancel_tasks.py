# -*- coding: utf-8 -*-


import sys

from kobo.client import ClientCommand


class Cancel_Tasks(ClientCommand):
    """cancel free, assigned or open tasks"""
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

        failed = False
        for task_id in tasks:
            try:
                self.hub.client.cancel_task(task_id)
            except Exception, ex:
                failed = True
                print ex

        if failed:
            sys.exit(1)
