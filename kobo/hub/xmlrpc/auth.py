# -*- coding: utf-8 -*-

import django.contrib.auth
from django.core.exceptions import PermissionDenied

from kobo.hub.models import Worker
from kobo.django.auth.krb5 import Krb5RemoteUserBackend
from kobo.django.xmlrpc.auth import *


__all__ = (
    "renew_session",
    "login_krbv",
    "login_password",
    "login_worker_key",
    "logout",
)


def login_worker_key(request, worker_key):
    """login_worker_key(worker_key): session_key"""
    try:
        worker = Worker.objects.get(worker_key=worker_key)
    except Worker.DoesNotExist:
        raise PermissionDenied()

    username = "worker/%s" % worker.name
    backend = Krb5RemoteUserBackend()
    user = backend.authenticate(username)
    if user is None:
        raise PermissionDenied()
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    user = django.contrib.auth.login(request, user)
    return request.session.session_key
