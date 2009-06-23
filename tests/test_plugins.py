#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest
import run_tests # set sys.path

from kobo.plugins import PluginContainer, Plugin


class PluginA(Plugin):
    enabled = True

class PluginB(Plugin):
    enabled = True

class PluginC(PluginB):
    enabled = True

class DisabledPlugin(Plugin):
    enabled = False

class MyContainer(PluginContainer):
    pass

class InheritedContainer(MyContainer):
    pass


class TestConf(unittest.TestCase):
    def setUp(self):
        PluginContainer._class_plugins = {}
        MyContainer._class_plugins = {}
        InheritedContainer._class_plugins = {}

    def test_register(self):
        self.assertRaises(TypeError, PluginContainer.register_plugin, PluginA)
        result = MyContainer.register_plugin(PluginA)
        self.assertEqual(result, "PluginA")

    def test_container_inheritance(self):
        MyContainer.register_plugin(PluginA)
        InheritedContainer.register_plugin(PluginB)
        InheritedContainer.register_plugin(PluginC)

        my_container = MyContainer()
        plugin_a = my_container["PluginA"]
        self.assertRaises(KeyError, my_container.__getitem__, "PluginB")
        self.assertRaises(KeyError, my_container.__getitem__, "PluginC")

        inherited_container = InheritedContainer()
        plugin_a = inherited_container["PluginA"]
        plugin_b = inherited_container["PluginB"]
        plugin_c = inherited_container["PluginC"]

    def test_disabled_plugin(self):
        result = MyContainer.register_plugin(DisabledPlugin)
        self.assertEqual(result, None)
        my_container = MyContainer()
        self.assertRaises(KeyError, my_container.__getitem__, "DisabledPlugin")


if __name__ == '__main__':
    unittest.main()
