#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import subprocess


def test_fields():
    # FIXME: this test should be refactored to work within the current
    # process.  Doing it this way, calling to a subprocess, will effectively
    # disable several features from the test framework.
    subprocess.check_call([sys.executable, __file__])


def main():
    # Runs the test under fields_test directory with custom settings
    PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.environ["PYTHONPATH"] = PROJECT_DIR
    os.environ['DJANGO_SETTINGS_MODULE'] = 'fields_test.settings'
    sys.path.insert(0, PROJECT_DIR)

    from django.core.management import call_command
    import django

    # Django >= 1.7 must call this method to initialize app registry,
    # while older Django do not have this method
    if 'setup' in dir(django):
        django.setup()

    call_command('test', 'fields_test')
    #call_command('syncdb')


if __name__ == '__main__':
    main()
