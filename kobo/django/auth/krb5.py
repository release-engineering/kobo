# -*- coding: utf-8 -*-


from django.conf import settings
from django.contrib.auth import login, SESSION_KEY
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ImproperlyConfigured


# TODO: http://code.djangoproject.com/ticket/689


def get_user(request):
    backend = Krb5Backend()
    try:
        user_id = request.session[SESSION_KEY]
        user = backend.get_user(user_id) or AnonymousUser()
    except:
        # TODO: catch only some exceptions
        user = AnonymousUser()

    # modification for kerberos
    # check for *AUTH_TYPE* and *username*,
    # authenticate user and automatically log in

    auth_type = request.META.get("AUTH_TYPE", None)
    if auth_type is not None and auth_type.lower() != "negotiate":
        return user

    username = request.META.get("REMOTE_USER", None)
    if username is None:
        return user

    # remove @REALM from username
    username = username.split("@")[0]

    # authenticate user
    user = backend.authenticate(username=username)
    user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)

    if type(user) is AnonymousUser or user.username == username:
        login(request, user)

    return user


class LazyUser(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, "_cached_user"):
            request._cached_user = get_user(request)
        return request._cached_user


class Krb5AuthenticationMiddleware(object):
    def __init__(self):
        # check if we have all variables in settings
        for var in ("KRB_PROXY_PRINCIPALS", "KRB_AUTH_PRINCIPAL", "KRB_AUTH_KEYTAB"):
            if not hasattr(settings, var):
                raise ImproperlyConfigured("Variable '%s' not set in settings." % var)

    def process_request(self, request):
        assert hasattr(request, "session"), "The Django authentication middleware requires session middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert \"django.contrib.sessions.middleware.SessionMiddleware\"."
        request.__class__.user = LazyUser()
        return None


class Krb5Backend(ModelBackend):
    """Authenticate using Kerberos"""
    def __init__(self, *args, **kwargs):
        if "kobo.django.auth.krb5.Krb5Backend" in getattr(settings, "AUTHENTICATION_BACKENDS", []):
            raise ImproperlyConfigured("Krb5Backend must not be listed in AUTHENTICATION_BACKENDS. It is for internal use in Krb5AuthenticationMiddleware only.")
        ModelBackend.__init__(self, *args, **kwargs)

    def authenticate(self, username=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # create a new user with unusable password
            user = User(username=username)
            user.set_unusable_password()
            user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
