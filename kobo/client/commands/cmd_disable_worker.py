# -*- coding: utf-8 -*-


import sys
from xmlrpclib import Fault

from kobo.client import ClientCommand


class Disable_Worker(ClientCommand):
    """disable worker"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s worker_name [worker_name]" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) == 0:
            self.parser.error("No worker specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        workers = args

        self.set_hub(username, password)
        for worker in workers:
            try:
                self.hub.client.disable_worker(worker)
            except Fault, ex:
                sys.stderr.write("%s\n" % ex.faultString)
