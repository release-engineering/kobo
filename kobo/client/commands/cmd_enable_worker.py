# -*- coding: utf-8 -*-


import sys
from six.moves.xmlrpc_client import Fault

from kobo.client import ClientCommand


class Enable_Worker(ClientCommand):
    """enable worker"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s [--all] [worker_name]" % self.normalized_name

        self.parser.add_option(
            "--all",
            default=False,
            action="store_true",
            help="Enable all enabled workers"
        )

    def run(self, *args, **kwargs):
        if len(args) == 0 and not kwargs['all']:
            self.parser.error("No worker (or --all) specified.")
        if len(args) and kwargs['all']:
            self.parser.error("Specify worker name or --all. From safety reasons both are not allowed.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        self.set_hub(username, password)
        if kwargs['all']:
            try:
                workers = self.hub.client.list_workers(True)
            except Fault as ex:
                sys.stderr.write("%s\n" % ex.faultString)
                sys.exit(1)
        else:
            workers = args
        for worker in workers:
            try:
                self.hub.client.enable_worker(worker)
            except Fault as ex:
                sys.stderr.write("%s\n" % ex.faultString)
