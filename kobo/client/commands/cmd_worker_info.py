# -*- coding: utf-8 -*-

from __future__ import print_function
from pprint import pprint
from kobo.client import ClientCommand


class Worker_Info(ClientCommand):
    """get worker info"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s worker_name" % self.normalized_name

        self.parser.add_option(
            "--oneline",
            default=False,
            action="store_true",
            help="Display one-line dict output instead of pretty-print"
        )


    def run(self, *args, **kwargs):
        if len(args) != 1:
            self.parser.error("No worker specified")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        worker_name = args[0]

        self.set_hub(username, password)
        result = self.hub.client.get_worker_info(worker_name)
        if kwargs.pop("oneline"):
            print(result)
        else:
            pprint(result)
