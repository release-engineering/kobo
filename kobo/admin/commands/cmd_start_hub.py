# -*- coding: utf-8 -*-


import os
import re

import kobo.cli
import kobo.admin
import kobo.shortcuts


class Start_Hub(kobo.cli.Command):
    """create a hub project directory structure in the current directory"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <project_name>" % self.normalized_name

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error("Please specify a name of the project.")

        name = args[0].replace("-", "_")
        directory = os.getcwd()

        try:
            kobo.admin.copy_helper(name, directory, "hub")
        except kobo.admin.TemplateError as ex:
            self.parser.error(ex)

        # code from django/core/management/commands/startproject.py
        # Create a random SECRET_KEY hash, and put it in the main settings.
        main_settings_file = os.path.join(directory, name, 'settings.py')
        settings_contents = open(main_settings_file, 'r').read()
        fp = open(main_settings_file, 'w')
        django_alphabet = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        secret_key = kobo.shortcuts.random_string(50, alphabet=django_alphabet)
        settings_contents = re.sub(r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)
        fp.write(settings_contents)
        fp.close()
