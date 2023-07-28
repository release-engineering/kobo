import sys
from xmlrpc.client import Fault
import json

from kobo.client import ClientCommand


class Create_Worker(ClientCommand):
    """create a worker"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s worker_name [worker_name]" % self.normalized_name

    def run(self, *args, **kwargs):
        if not args:
            self.parser.error("No worker name specified.")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        hub = kwargs.pop("hub", None)
        workers = args

        self.set_hub(username, password, hub)
        for worker in workers:
            try:
                new_worker = self.hub.client.create_worker(worker)
                print(json.dumps(new_worker))
            except Fault as ex:
                print(repr(ex), file=sys.stderr)
                # Exit on first xmlrpc failure
                # It's very likely user is not admin
                raise
