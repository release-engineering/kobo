# -*- coding: utf-8 -*-


import datetime
import base64
import socket
import json
import time

import django.contrib.auth
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from django.contrib.sessions.models import Session

from kobo.django.auth.krb5 import Krb5RemoteUserBackend
from kobo.django.django_version import django_version_ge
from kobo.django.helpers import call_if_callable


__all__ = (
    "renew_session",
    "login_krbv",
    "login_password",
    "login_oidc",
    "logout",
)


def renew_session(request):
    """renew_session(): bool

    Renew current session. Return True if session is no longer valid and user should log in.
    """

    request.session.modified = True
    return not call_if_callable(request.user.is_authenticated)


def login_password(request, username, password):
    """login_password(username, password): session_id"""
    backend = ModelBackend()
    if django_version_ge('1.11.0'):
        user = backend.authenticate(None, username, password)
    else:
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
    decode_func = base64.decodebytes if hasattr(base64, "decodebytes") else base64.decodestring
    decoded_request = decode_func(krb_request)
    auth_context, opts, server_principal, cache_credentials = context.rd_req(decoded_request, server=server_principal, keytab=server_keytab, auth_context=auth_context, options=krbV.AP_OPTS_MUTUAL_REQUIRED)
    cprinc = cache_credentials[2]

    # remove @REALM
    username = cprinc.name.split("@")[0]
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

def login_oidc(request, json_web_token):
    import jwcrypto.jwk
    import jwcrypto.jwt
    import requests_cache

    session = requests_cache.CachedSession("public-keys")
    response = session.get(settings.OIDC_PUBLIC_KEY_URL)
    keys = [jwcrypto.jwk.JWK(**key) for key in response.json()["keys"]]

    decoded_jwt = None
    for key in keys:
        try:
            decoded_jwt = json.loads(jwcrypto.jwt.JWT(jwt=json_web_token, key=key).claims)
        except:
            pass
        else:
            break

    if not decoded_jwt:
        raise PermissionDenied("JWT's signature couldn't be verified with any public key")
    if decoded_jwt.get("exp", 0) <= int(time.time()):
        raise PermissionDenied("Authentication was attempted with an expired JWT")

    backend = Krb5RemoteUserBackend()
    if django_version_ge("1.11.0"):
        user = backend.authenticate(None, decoded_jwt["clientId"])
    else:
        user = backend.authenticate(decoded_jwt["clientId"])
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
