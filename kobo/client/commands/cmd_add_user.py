# -*- coding: utf-8 -*-


import sys
from xmlrpclib import Fault

from kobo.client import ClientCommand


class Add_User(ClientCommand):
    """add a new user"""
    enabled = True
    admin = True


    def options(self):
        self.parser.usage = "%%prog %s [options] <user>" % self.normalized_name

        self.parser.add_option(
            "--admin",
            default=False,
            action="store_true",
            help="grant admin privileges"
        )


    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a user")

        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)
        admin = kwargs.pop("admin", False)
        user = args[0]

        self.set_hub(username, password)
        try:
            self.hub.admin.add_user(user, admin)
        except Exception, ex:
            print str(ex)
            sys.exit(1)
