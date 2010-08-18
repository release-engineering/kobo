# -*- coding: utf-8 -*-


import os

import kobo.cli
import kobo.admin


class Start_Client(kobo.cli.Command):
    """create a hub client project directory structure in the current directory"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <project_name>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a name of the project.")

        name = args[0]
        directory = os.getcwd()

        try:
            kobo.admin.copy_helper(name, directory, "client")
        except kobo.admin.TemplateError, ex:
            self.parser.error(ex)

        print "Edit config file to finish setup."
        print "Use `kobo-admin start-client-command` to add additional commands."
