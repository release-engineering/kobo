# -*- coding: utf-8 -*-


import os


__all__ = (
    "Plugin",
    "PluginContainer",
)


class Plugin(object):
    """A plugin base class."""

    __slots__ = (
        "author",
        "version",
        "enabled",
        "container",
    )

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

    __slots__ = (
        "lower_case",
        "_plugins"
    )

    lower_case = False


    def __getitem__(self, name):
        return self._get_plugin(name)


    def __iter__(self):
        return self.plugins.iterkeys()


    @classmethod
    def normalize_name(cls, name):
        result = name
        if getattr(cls, "lower_case", False):
            return result.lower()
        return result


    @classmethod
    def _get_plugins(cls):
        """Return dictionary of registered plugins."""
        all_plugins = []
        if hasattr(cls, "_class_plugins"):
            all_plugins += cls._class_plugins.values()
        all_plugins += cls._get_parent_plugins()

        plugins = {}
        for plugin_class in all_plugins:
            name = plugin_class.__name__
            normalized_name = cls.normalize_name(name)
            if normalized_name in plugins:
               raise RuntimeError("Cannot register plugin '%s'. Another plugin with the same normalized name (%s) is already in the container." % (name, normalized_name))
            plugins[normalized_name] = type(plugin_class.__name__, (plugin_class, ), {"container": cls})
        return plugins


    @classmethod
    def _get_parent_plugins(cls):
        result = []
        for parent in cls.__bases__:
            if parent is PluginContainer:
                # don't use PluginContainer itself - plugins have to be registered to subclasses
                continue

            if not issubclass(parent, PluginContainer):
                # skip parents which are not PluginContainer subclasses
                continue

            if hasattr(parent, "_class_plugins"):
                result.extend(parent._class_plugins.values())
            result.extend(parent._get_parent_plugins())

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

        return self.plugins[normalized_name]


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
    def register_module(cls, module, prefix=None):
        """Register all plugins in a module's submodules."""
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

        __import__(module.__name__, {}, {}, module_list)

        for mn in module_list:
            mod = getattr(module, mn)
            for pn in dir(mod):
                plugin = getattr(mod, pn)
                if type(plugin) is type and issubclass(plugin, Plugin) and plugin is not Plugin:
                    cls.register_plugin(plugin)
