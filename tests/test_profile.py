#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest2 as unittest
import os

from kobo.client import BaseClientCommandContainer
from kobo.cli import CommandOptionParser


class TestCommandContainer(BaseClientCommandContainer):
    pass


class TestConf(unittest.TestCase):
    def setUp(self):
        self.command_container = TestCommandContainer()

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
