#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import os
import tempfile
import shutil

from kobo.client import BaseClientCommandContainer, ClientCommandContainer
from kobo.cli import CommandOptionParser
from kobo.conf import PyConfigParser

TEST_CONFIG = '''
HUB_URL = "https://localhost/hub/xmlrpc"

AUTH_METHOD = "krbv"
'''


class TestBaseClientCommandContainer(unittest.TestCase):
    def setUp(self):
        self.command_container = BaseClientCommandContainer()

    def test_profile_option_unset(self):
        parser = CommandOptionParser(command_container=self.command_container)
        option = parser.get_option("--profile")

        self.assertEqual(parser.default_profile, "")
        self.assertEqual(option, None)

    def test_profile_option_set(self):
        parser = CommandOptionParser(command_container=self.command_container, default_profile="default-profile")
        option = parser.get_option("--profile")

        self.assertEqual(parser.default_profile, "default-profile")
        self.assertEqual(option.get_opt_string(), "--profile")
        self.assertEqual(option.help, "specify profile (default: default-profile)")

    def test_configuration_directory_option_unset(self):
        parser = CommandOptionParser(command_container=self.command_container, default_profile="default-profile")
        # CommandOptionParser() doesn't store the configuration_file path in an instance variable, instead it's
        # build in _load_profile() with the line below:
        configuration_file = os.path.join(parser.configuration_directory, '{0}.conf'.format(parser.default_profile))

        self.assertEqual(parser.configuration_directory, "/etc")
        self.assertEqual(configuration_file, "/etc/default-profile.conf")

    def test_configuration_directory_option_set(self):
        parser = CommandOptionParser(command_container=self.command_container, default_profile="default-profile",
                                     configuration_directory="/etc/client")

        configuration_file = os.path.join(parser.configuration_directory, '{0}.conf'.format(parser.default_profile))

        self.assertEqual(parser.configuration_directory, "/etc/client")
        self.assertEqual(configuration_file, "/etc/client/default-profile.conf")


class TestClientCommandContainer(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.conf = PyConfigParser()

        self.file = os.path.join(self.dir, 'test.conf')

        with open(self.file, 'w') as f:
            f.write(TEST_CONFIG)

        self.conf.load_from_file(self.file)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_config_from_file(self):
        container = ClientCommandContainer(self.conf)

        values = {
            'HUB_URL': 'https://localhost/hub/xmlrpc',
            'AUTH_METHOD': 'krbv'
        }
        self.assertEqual(container.conf, values)

    def test_config_from_kwargs(self):
        container = ClientCommandContainer(self.conf, USERNAME='testuser')

        values = {
            'HUB_URL': 'https://localhost/hub/xmlrpc',
            'AUTH_METHOD': 'krbv',
            'USERNAME': 'testuser'
        }
        self.assertEqual(container.conf, values)
