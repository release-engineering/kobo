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

class ContainerA(PluginContainer):
    pass

class ContainerB(ContainerA):
    pass

class ContainerC(ContainerB):
    @classmethod
    def normalize_name(cls, name):
        return name.upper()


class TestConf(unittest.TestCase):
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
        self.assert_("PluginA" not in container_c)
        self.assert_("PluginB" not in container_c)
        self.assert_("PluginC" not in container_c)
        self.assert_("PLUGINA" in container_c)
        self.assert_("PLUGINB" in container_c)
        self.assert_("PLUGINC" in container_c)

        container_b = ContainerB()
        self.assert_("PluginA" in container_b)
        self.assert_("PluginB" in container_b)
        self.assert_("PluginC" not in container_b)


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
        self.assertEqual(container_a["PluginA"].container, container_a.__class__)

        container_b = ContainerB()
        self.assertEqual(container_b["PluginA"].container, container_b.__class__)
        self.assertEqual(container_b["PluginB"].container, container_b.__class__)

        container_c = ContainerC()
        self.assertEqual(container_c["PluginA"].container, container_c.__class__)
        self.assertEqual(container_c["PluginB"].container, container_c.__class__)
        self.assertEqual(container_c["PluginC"].container, container_c.__class__)


    def test_disabled_plugin(self):
        result = ContainerA.register_plugin(DisabledPlugin)
        self.assertEqual(result, None)
        container_a = ContainerA()
        self.assertRaises(KeyError, container_a.__getitem__, "DisabledPlugin")


    def test_same_normalized_name(self):
        class PLUGINA(Plugin):
            enabled = True

        ContainerA.register_plugin(PluginA)
        container_a = ContainerA()

        ContainerC.register_plugin(PLUGINA)
        container_c = ContainerC()
        self.assertRaises(RuntimeError, getattr, container_c, "plugins")


if __name__ == '__main__':
    unittest.main()
