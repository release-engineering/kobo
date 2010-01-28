# -*- coding: utf-8 -*-


import socket

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from kobo.decorators import decorator_with_args
from kobo.django.xmlrpc.decorators import *


def validate_worker(func):
    def _new_func(request, *args, **kwargs):
        if not request.user.is_authenticated():
            raise PermissionDenied("Login required.")

        if getattr(request, 'worker', None) is None:
            raise SuspiciousOperation("User doesn't match any worker: %s" % request.user.username)

        fqdn = socket.getfqdn(request.META["REMOTE_ADDR"])
        prefix, hostname = request.user.username.split("/", 1)
        if hostname != fqdn:
            raise SuspiciousOperation("Worker's FQDN (%s) doesn't match username (%s)" % (fqdn, hostname))

        return func(request, *args, **kwargs)

    _new_func.__name__ = func.__name__
    _new_func.__doc__ = func.__doc__
    _new_func.__dict__.update(func.__dict__)
    return _new_func
