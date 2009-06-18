# -*- coding: utf-8 -*-


__all__ = (
    "Enum",
    "DictSet",
)


class Enum(object):
    __slots__ = (
        "_dict",
        "_order",
    )


    def __init__(self, *args):
        self._order = args
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
        return [ (self._dict[key], key) for key in self._order ]


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
