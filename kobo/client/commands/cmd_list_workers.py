# -*- coding: utf-8 -*-


from __future__ import print_function
from kobo.client import ClientCommand


class List_Workers(ClientCommand):
    """list workers"""
    enabled = True


    def options(self):
        self.parser.usage = "%%prog %s" % self.normalized_name

        self.parser.add_option(
            "--show-disabled",
            default=False,
            action="store_true",
            help="show disabled workers"
        )


    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        show_disabled = kwargs.get("show_disabled", False)

        self.set_hub(username, password)
        print(self.hub.client.list_workers(not show_disabled))
