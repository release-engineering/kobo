# -*- coding: utf-8 -*-


import datetime
import base64
import socket

import django.contrib.auth
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist

from kobo.hub.models import Worker
from kobo.django.auth.krb5 import Krb5RemoteUserBackend
from kobo.django.xmlrpc.auth import *
from kobo.django.django_version import django_version_ge


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
    except ObjectDoesNotExist:
        raise PermissionDenied()

    username = "worker/%s" % worker.name
    backend = Krb5RemoteUserBackend()
    if django_version_ge('1.11.0'):
        user = backend.authenticate(None, username)
    else:
        user = backend.authenticate(username)
    if user is None:
        raise PermissionDenied()
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    user = django.contrib.auth.login(request, user)
    return request.session.session_key
