# -*- coding: utf-8 -*-


class ImproperlyConfigured(Exception):
    """Program is improperly configured."""
    pass


class ShutdownException(Exception):
    """Shutdown currently running program."""
    pass
