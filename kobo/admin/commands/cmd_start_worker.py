# -*- coding: utf-8 -*-


import os

import kobo.cli
import kobo.admin


class Start_Worker(kobo.cli.Command):
    """create a worker directory structure in the current directory"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <project_name>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a name of the project.")

        name = args[0]
        directory = os.getcwd()

        try:
            kobo.admin.copy_helper(name, directory, "worker")
        except kobo.admin.TemplateError as ex:
            self.parser.error(ex)
