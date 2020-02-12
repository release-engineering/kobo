# -*- coding: utf-8 -*-


import datetime
import base64
import socket

import django.contrib.auth
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from django.contrib.sessions.models import Session

from kobo.django.auth.krb5 import Krb5RemoteUserBackend


__all__ = (
    "renew_session",
    "login_krbv",
    "login_gssapi",
    "login_password",
    "logout",
)


def renew_session(request):
    """renew_session(): bool

    Renew current session. Return True if session is no longer valid and user should log in.
    """

    request.session.modified = True
    return not request.user.is_authenticated()


def login_password(request, username, password):
    """login_password(username, password): session_id"""
    backend = ModelBackend()
    user = backend.authenticate(username, password)
    if user is None:
        raise PermissionDenied("Invalid username or password.")
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    django.contrib.auth.login(request, user)
    return request.session.session_key


# TODO: proxy_user
def login_krbv(request, krb_request, proxy_user=None):
    """login_krbv(krb_request, proxy_user=None): session_key"""
    import krbV

    context = krbV.default_context()
    server_principal = krbV.Principal(name=settings.KRB_AUTH_PRINCIPAL, context=context)
    server_keytab = krbV.Keytab(name=settings.KRB_AUTH_KEYTAB, context=context)

    auth_context = krbV.AuthContext(context=context)
    auth_context.flags = krbV.KRB5_AUTH_CONTEXT_DO_SEQUENCE | krbV.KRB5_AUTH_CONTEXT_DO_TIME
    auth_context.addrs = (socket.gethostbyname(request.META["HTTP_HOST"]), 0, request.META["REMOTE_ADDR"], 0)

    # decode and read the authentication request
    decoded_request = base64.decodestring(krb_request)
    auth_context, opts, server_principal, cache_credentials = context.rd_req(decoded_request, server=server_principal, keytab=server_keytab, auth_context=auth_context, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
    cprinc = cache_credentials[2]

    # remove @REALM
    username = cprinc.name.split("@")[0]
    backend = Krb5RemoteUserBackend()
    user = backend.authenticate(username)
    if user is None:
        raise PermissionDenied()
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    django.contrib.auth.login(request, user)
    return request.session.session_key


def login_gssapi(request, krb_request, proxy_user=None):
    #For python versions older than 3.4, enum34 package has to be installed
    import enum
    import gssapi

    name = gssapi.Name(settings.KRB_AUTH_PRINCIPAL, gssapi.NameType.kerberos_principal)
    store = {'keytab': settings.KRB_AUTH_KEYTAB}
    server_credentials = gssapi.Credentials(name=name, store=store, usage='accept',
                                            mechs=[gssapi.MechType.kerberos])

    flags = 0x00000004 | 0x00000001
    bindings = gssapi.raw.ChannelBindings(
        initiator_address_type=2, initiator_address=request.META["REMOTE_ADDR"],
        acceptor_address_type=2, acceptor_address=socket.gethostbyname(request.META["HTTP_HOST"]))
    server_context = gssapi.SecurityContext(
        creds=server_credentials, flags=flags, usage='accept', channel_bindings=bindings)
    server_context.step(krb_request)
    client_name = str(gssapi.Name(token=krb_request))

    username = client_name.split("@")[0]
    backend = Krb5RemoteUserBackend()
    if django_version_ge('1.11.0'):
        user = backend.authenticate(None, username)
    else:
        user = backend.authenticate(username)
    if user is None:
        raise PermissionDenied()
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)
    django.contrib.auth.login(request, user)
    return request.session.session_key


def logout(request):
    """logout()

    Delete session information.
    """
    django.contrib.auth.logout(request)
