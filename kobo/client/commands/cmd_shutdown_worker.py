# -*- coding: utf-8 -*-


import sys
from six.moves.xmlrpc_client import Fault

from kobo.client import ClientCommand


class Shutdown_Worker(ClientCommand):
    """shutdown a worker"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s [--kill] worker_name [worker_name]" % self.normalized_name

        self.parser.add_option(
            "--kill",
            default=False,
            action="store_true",
            help="kill worker immediately"
        )


    def run(self, *args, **kwargs):
        kill = kwargs.pop("kill", False)

        if len(args) == 0:
            self.parser.error("No worker specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        hub = kwargs.pop("hub", None)
        workers = args

        self.set_hub(username, password, hub)
        for worker in workers:
            try:
                self.hub.client.shutdown_worker(worker, kill)
            except Fault as ex:
                print(repr(ex), file=sys.stderr)
