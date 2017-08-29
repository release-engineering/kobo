# -*- coding: utf-8 -*-


import os

import kobo.cli
import kobo.admin


class Start_Worker_Task(kobo.cli.Command):
    """create a worker task module in the current directory"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <task_name>" % self.normalized_name
        self.parser.add_option("-d", "--dir", help="target directory")

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a name of the task.")

        name = args[0]
        directory = kwargs.pop("dir")
        if not directory:
            directory = os.getcwd()

        try:
            kobo.admin.copy_helper(name, directory, "task___project_name__.py.template")
        except kobo.admin.TemplateError as ex:
            self.parser.error(ex)
