# -*- coding: utf-8 -*-


__all__ = (
    "Enum",
    "EnumItem",
    "DictSet",
)


class EnumItem(object):
    """Data wrapper for Enum."""
    __slots__ = (
        "name",
        "help_text",
        "options",
    )

    def __init__(self, name, help_text=None, **kwargs):
        self.name = name
        self.help_text = help_text or ""
        self.options = kwargs


    def __str__(self):
        return self.name


    def __repr__(self):
        return str(self)


    def __eq__(self, obj):
        return str(self) == str(obj)


    def __getitem__(self, name):
        return self.options[name]


    def get(self, name, default=None):
        return self.options.get(name, default)


class Enum(object):
    """Enumerated list."""
    __slots__ = (
        "_dict",
        "_order",
        "_items",
    )


    def __init__(self, *args):
        """
        @param args: items to be enumerated
        @type args: str, EnumItem
        """
        self._items = []
        self._order = []
        
        for i in args:
            if type(i) is not EnumItem:
                i = EnumItem(str(i))
            self._items.append(i)
            self._order.append(str(i))

        self._dict = dict([ (value, i) for i, value in enumerate(self._order) ])


    def __iter__(self):
        return iter(self._order)


    def __getitem__(self, key):
        if type(key) in (int, slice):
            return self._order[key]
        return self._dict[key]


    def get(self, key, default=None):
        try:
            return self[key]
        except (IndexError, KeyError):
            return default


    def get_num(self, key, default=None):
        try:
            return self._dict[key]
        except (IndexError, KeyError):
            return default


    def get_value(self, key, default=None):
        try:
            return self._order[key]
        except (IndexError, KeyError):
            return default


    def get_mapping(self):
        """Return list of (key, value) mappings."""
        return [ (self._dict[key], key) for key in self._order ]


    def get_item(self, key):
        if type(key) is int:
            return self._items[key]
        return self._items[self._dict[key]]


    def get_item_help_text(self, key):
        """Return item's help text."""
        return self.get_item(key).help_text


    def get_item_option(self, key, option, default=None):
        """Return item's option passed as a kwarg in it's constructor."""
        return self.get_item(key).get(option, default)


class DictSet(dict):
    """Dictionary with set operations on keys."""


    def copy(self):
        return DictSet(super(DictSet, self).copy())


    def __sub__(self, other):
        result = DictSet()
        for key, value in self.iteritems():
            if key not in other:
                result[key] = value
        return result


    def __or__(self, other):
        result = self.copy()
        result.update(other)
        return result


    def __and__(self, other):
        result = DictSet()
        for key, value in self.iteritems():
            if key in other:
                result[key] = value
        return result


    def add(self, key, value):
        # return True if a new key was added
        if key in self:
            return False
        self[key] = value
        return True


    def remove(self, key):
        del self[key]
