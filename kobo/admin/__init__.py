# -*- coding: utf-8 -*-
# kobo-admin script, inspired by django-admin


import re
import os
import sys
import shutil

import kobo.cli
from kobo.types import Enum, EnumItem

import kobo.admin.commands


__all__ = (
    "TemplateError",
    "KoboAdminCommandContainer",
    "main",
    "copy_helper",
)


class TemplateError(Exception):
    """Processing of kobo directory structure template failed."""
    pass


# Inherit container to make sure nobody will change plugins I registered.
class KoboAdminCommandContainer(kobo.cli.CommandContainer):
    pass


def main():
    """Main method for kobo-admin script."""
    # Register plugins for commands
    KoboAdminCommandContainer.register_module(kobo.admin.commands, prefix="cmd_")

    command_container = KoboAdminCommandContainer()
    parser = kobo.cli.CommandOptionParser(
        command_container = command_container,
    )
    parser.run()
    return 0


def _camelize(name, fill_char=""):
    words = name.split('_')
    capwords = []
    for word in words:
        capwords.append(word.capitalize())
    return fill_char.join(capwords)


def _copy_file(path_old, path_new, name):
    # HACK: use .template suffix to prevent .py file byte compiling
    if path_new.endswith(".template"):
        path_new = path_new[:-9]

    fp_old = open(path_old, 'r')
    fp_new = open(path_new, 'w')

    # following django template sysntax
    fp_new.write(fp_old.read()\
        .replace('{{ project_name }}', name)\
        .replace('{{ project_name|upper }}', name.upper())\
        .replace('{{ project_name|camel }}', _camelize(name))\
        .replace('{{ project_name|camel_cmd }}', _camelize(name, fill_char="_"))
    )
    fp_old.close()
    fp_new.close()

    # copy permissions
    try:
        shutil.copymode(path_old, path_new)
    except OSError:
        sys.stderr.write("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new)


# based on django.core.management.base.copy_helper()
def copy_helper(name, directory, template_name):
    """Copies kobo based layout template into a specified directory."""

    # automatically convert dashes to underscores
    name = name.replace("-", "_")

    # name check from django
    if not re.search(r'^[_a-zA-Z]\w*$', name): # If it's not a valid directory name.
        # Provide a smart error message, depending on the error.
        if not re.search(r'^[_a-zA-Z]', name):
            message = 'make sure the name begins with a letter or underscore'
        else:
            message = 'use only numbers, letters and underscores'
        raise TemplateError("%r is not a valid name. Please %s." % (name, message))

    template_path = os.path.join(kobo.__path__[0], 'admin', 'templates', template_name)

    if os.path.isfile(template_path):
        path_new = os.path.join(directory, template_name).replace('__project_name__', name)
        path_new = path_new[path_new.find("@")+1:] # HACK: allow to have 2 source names (different prefix) with the same target names
        _copy_file(template_path, path_new, name)
        return

    top_dir = os.path.join(directory, name)
    try:
        os.mkdir(top_dir)
    except OSError, ex:
        raise TemplateError(ex)

    for dirname, subdirs, files in os.walk(template_path):
        relative_dir = dirname[len(template_path)+1:].replace('__project_name__', name)

        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))

        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo"):
                continue
            path_old = os.path.join(dirname, f)
            path_new = os.path.join(top_dir, relative_dir, f).replace('__project_name__', name)
            _copy_file(path_old, path_new, name)
