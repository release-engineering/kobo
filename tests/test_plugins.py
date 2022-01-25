#!/usr/bin/python
# -*- coding: utf-8 -*-


import unittest

from kobo.plugins import PluginContainer, Plugin


class PluginA(Plugin):
    enabled = True

class PluginB(Plugin):
    enabled = True

class PluginC(PluginB):
    enabled = True

class DisabledPlugin(Plugin):
    enabled = False

class ContainerA(PluginContainer):
    pass

class ContainerB(ContainerA):
    pass

class ContainerC(ContainerB):
    @classmethod
    def normalize_name(cls, name):
        return name.upper()

class ContainerD(PluginContainer):
    pass

class ContainerE(ContainerC, ContainerD):
    @classmethod
    def normalize_name(cls, name):
        return name.upper()


class TestPlugins(unittest.TestCase):
    def setUp(self):
        ContainerA._class_plugins = {}
        ContainerB._class_plugins = {}
        ContainerC._class_plugins = {}


    def test_register(self):
        self.assertRaises(TypeError, PluginContainer.register_plugin, PluginA)
        result = ContainerA.register_plugin(PluginA)
        self.assertEqual(result, "PluginA")


    def test_container_inheritance(self):
        ContainerA.register_plugin(PluginA)
        ContainerB.register_plugin(PluginB)
        ContainerC.register_plugin(PluginC)

        container_a = ContainerA()
        plugin_a = container_a["PluginA"]
        self.assertRaises(KeyError, container_a.__getitem__, "PluginB")
        self.assertRaises(KeyError, container_a.__getitem__, "PluginC")

        container_c = ContainerC()
        self.assertTrue("PluginA" not in container_c)
        self.assertTrue("PluginB" not in container_c)
        self.assertTrue("PluginC" not in container_c)
        self.assertTrue("PLUGINA" in container_c)
        self.assertTrue("PLUGINB" in container_c)
        self.assertTrue("PLUGINC" in container_c)

        container_b = ContainerB()
        self.assertTrue("PluginA" in container_b)
        self.assertTrue("PluginB" in container_b)
        self.assertTrue("PluginC" not in container_b)

        self.assertEqual(container_a["PluginA"].normalized_name, "PluginA")
        self.assertEqual(container_b["PluginA"].normalized_name, "PluginA")
        self.assertEqual(container_c["PluginA"].normalized_name, "PLUGINA")


    def test_class_attributes(self):
        ContainerA.register_plugin(PluginA)
        ContainerB.register_plugin(PluginB)
        container_a = ContainerA()
        container_b = ContainerB()

        # containers must make their own plugin class copies on creating an instance
        # it ensures that class attributes are specific just for one container
        container_a["PluginA"].foo = "FOO"
        self.assertEqual(getattr(container_b["PluginA"], "foo", None), None)


    def test_container_reference(self):
        ContainerA.register_plugin(PluginA)
        ContainerB.register_plugin(PluginB)
        ContainerC.register_plugin(PluginC)

        container_a = ContainerA()
        self.assertEqual(container_a["PluginA"].container, container_a)

        container_b = ContainerB()
        self.assertEqual(container_b["PluginA"].container, container_b)
        self.assertEqual(container_b["PluginB"].container, container_b)

        container_c = ContainerC()
        self.assertEqual(container_c["PluginA"].container, container_c)
        self.assertEqual(container_c["PluginB"].container, container_c)
        self.assertEqual(container_c["PluginC"].container, container_c)


    def test_disabled_plugin(self):
        result = ContainerA.register_plugin(DisabledPlugin)
        self.assertEqual(result, None)
        container_a = ContainerA()
        self.assertRaises(KeyError, container_a.__getitem__, "DisabledPlugin")


    def test_same_normalized_name(self):
        class PLUGINA(Plugin):
            enabled = True

        class pluginA(Plugin):
            enabled = True

        ContainerA.register_plugin(PluginA)
        container_a = ContainerA()

        ContainerD.register_plugin(PLUGINA)
        container_d = ContainerD()

        container_e = ContainerE()
        self.assertRaises(RuntimeError, getattr, container_e, "plugins")

    def test_skip_broken(self):
        from . import plugins
        self.assertRaises(RuntimeError, ContainerA.register_module, plugins)

        ContainerA.register_module(plugins, skip_broken=True)
        container_a = ContainerA()
        container_a["WorkingPlugin"]
        self.assertRaises(KeyError, container_a.__getitem__, "BrokenPlugin")
