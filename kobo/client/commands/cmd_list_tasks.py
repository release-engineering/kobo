# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
try:
    import json
except ImportError:
    import simplejson as json

from kobo.client import ClientCommand
from kobo.client.constants import TASK_STATES


class List_Tasks(ClientCommand):
    """list RUNNING and/or FREE tasks"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s [--free] [--running] [--verbose|--json]" % self.normalized_name

        self.parser.add_option(
            "--running",
            default=False,
            action="store_true",
            help="list RUNNING tasks"
        )

        self.parser.add_option(
            "--free",
            default=False,
            action="store_true",
            help="list FREE tasks",
        )

        self.parser.add_option(
            "--verbose",
            default=False,
            action="store_true",
            help="print details",
        )

        self.parser.add_option(
            "--json",
            default=False,
            action="store_true",
            help="print results in json",
        )

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        verbose = kwargs.pop("verbose", False)
        use_json = kwargs.pop("json", False)

        if verbose and use_json:
            self.parser.error("It has no sense to use --verbose and --json in one time.")

        filters = []
        if kwargs['free']:
            filters += [TASK_STATES["FREE"], TASK_STATES["CREATED"]]
        if kwargs['running']:
            filters += [TASK_STATES["ASSIGNED"], TASK_STATES["OPEN"]]

        if not filters:
            self.parser.error("Use at least one from --free or --running options.")

        self.set_hub(username, password)
        result = sorted(self.hub.client.get_tasks([], filters), key=lambda x: x["id"])
        if use_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        elif verbose:
            fmt = "%(id)8s %(state_label)-12s %(method)-20s %(owner)-12s %(worker)s"
            header = dict(id="TASKID", state_label="STATE", method="METHOD", owner="OWNER", worker="WORKER")
            print(fmt % header, file=sys.stderr)
            for task in result:
                print(fmt % task)
        else:
            for task in result:
                print(task['id'])
