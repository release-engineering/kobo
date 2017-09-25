# -*- coding: utf-8 -*-


"""
IMPORTANT: Avoid cycles in container inheritance.

If you need multiple inheritance, never do this:
  - class A(PluginContainer)
  - class B(A)
  - class C(A)
  - class D(B, C) # wrong! both C and B inherit from A; this ends with TypeError: Cannot create a consistent method resolution order (MRO)...

Always make sure all trees inherit from PluginContainer:
  - class A(PluginContainer)
  - class B(A)
  - class C(PluginContainer)
  - class D(C)
  - class E(C, D) # correct, the only common predecesor is PluginContainer
"""


from __future__ import print_function
import os
import six


__all__ = (
    "Plugin",
    "PluginContainer",
)


class Plugin(object):
    """A plugin base class."""

    author = None
    version = None
    enabled = False

    def __getattr__(self, name):
        """
        Get missing attribute from a container.
        This is quite hackish but it allows to define settings and methods per container.
        """
        return getattr(self.container, name)


class PluginContainer(object):
    """A plugin container.

    Usage: Inherit PluginContainer and register plugins to the new class.
    """

    def __getitem__(self, name):
        return self._get_plugin(name)

    def __iter__(self):
        return iter(self.plugins)

    @classmethod
    def normalize_name(cls, name):
        return name

    @classmethod
    def _get_plugins(cls):
        """Return dictionary of registered plugins."""

        result = {}
        parent_plugins = list(cls._get_parent_plugins(cls.normalize_name).items())
        class_plugins = list(getattr(cls, "_class_plugins", {}).items())
        for name, plugin_class in parent_plugins + class_plugins:
            result[name] = type(plugin_class.__name__, (plugin_class, ), {"__doc__": plugin_class.__doc__})
        return result

    @classmethod
    def _get_parent_plugins(cls, normalize_function):
        result = {}
        for parent in cls.__bases__:
            if parent is PluginContainer:
                # don't use PluginContainer itself - plugins have to be registered to subclasses
                continue

            if not issubclass(parent, PluginContainer):
                # skip parents which are not PluginContainer subclasses
                continue

            # read inherited plugins first (conflicts are resolved recursively)
            plugins = parent._get_parent_plugins(normalize_function)

            # read class plugins, override inherited on name conflicts
            if hasattr(parent, "_class_plugins"):
                for plugin_class in parent._class_plugins.values():
                    normalized_name = normalize_function(plugin_class.__name__)
                    plugins[normalized_name] = plugin_class

            for name, value in six.iteritems(plugins):
                if result.get(name, value) != value:
                   raise RuntimeError("Cannot register plugin '%s'. Another plugin with the same normalized name (%s) is already in the container." % (str(value), normalized_name))

            result.update(plugins)

        return result

    @property
    def plugins(self):
        if not hasattr(self, "_plugins"):
            self._plugins = self.__class__._get_plugins()
        return self._plugins

    def _get_plugin(self, name):
        """Return a plugin or raise KeyError."""
        normalized_name = self.normalize_name(name)

        if normalized_name not in self.plugins:
            raise KeyError("Plugin not found: %s" % normalized_name)

        plugin = self.plugins[normalized_name]
        plugin.container = self
        plugin.normalized_name = normalized_name
        return plugin

    @classmethod
    def register_plugin(cls, plugin):
        """Register a new plugin. Return normalized plugin name."""

        if cls is PluginContainer:
            raise TypeError("Can't register plugin to the PluginContainer base class.")

        if "_class_plugins" not in cls.__dict__:
            cls._class_plugins = {}

        if not getattr(plugin, "enabled", False):
            return

        normalized_name = cls.normalize_name(plugin.__name__)
        cls._class_plugins[normalized_name] = plugin
        return normalized_name

    @classmethod
    def register_module(cls, module, prefix=None, skip_broken=False):
        """Register all plugins in a module's sub-modules.

        @param module: a python module that contains plugin sub-modules
        @type  module: module
        @param prefix: if specified, only modules with this prefix will be processed
        @type  prefix: str
        @param skip_broken: skip broken sub-modules and print a warning
        @type  skip_broken: bool
        """
        path = os.path.dirname(module.__file__)
        module_list = []

        for fn in os.listdir(path):
            if not fn.endswith(".py"):
                continue
            if fn.startswith("_"):
                continue
            if prefix and not fn.startswith(prefix):
                continue
            if not os.path.isfile(os.path.join(path, fn)):
                continue
            module_list.append(fn[:-3])

        if skip_broken:
            for mod in module_list[:]:
                try:
                    __import__(module.__name__, {}, {}, [mod])
                except:
                    import sys
                    print("WARNING: Skipping broken plugin module: %s.%s" % (module.__name__, mod), file=sys.stderr)
                    module_list.remove(mod)
        else:
            __import__(module.__name__, {}, {}, module_list)

        for mn in module_list:
            mod = getattr(module, mn)
            for pn in dir(mod):
                plugin = getattr(mod, pn)
                if type(plugin) is type and issubclass(plugin, Plugin) and plugin is not Plugin:
                    cls.register_plugin(plugin)
