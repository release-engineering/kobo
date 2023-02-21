# -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
import os
import datetime
import inspect

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from kobo.decorators import decorator_with_args
from kobo.django.helpers import call_if_callable
from kobo.shortcuts import random_string
from kobo.tback import Traceback

from .models import XmlRpcLog
import six
from six.moves import zip


__all__ = (
    "user_passes_test",
    "login_required",
    "admin_required",
    "validate_user",
    "log_call",
    "log_traceback",
)

LOG = logging.getLogger(__name__)

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

@decorator_with_args
def user_passes_test(func, test_func):
    def _new_func(request, *args, **kwargs):
        if not test_func(request.user):
            message = "Permission denied."
            raise PermissionDenied(message)
        return func(request, *args, **kwargs)

    _new_func.__name__ = func.__name__
    _new_func.__doc__ = func.__doc__
    _new_func.__dict__.update(func.__dict__)
    return _new_func


def login_required(func):
    def _new_func(request, *args, **kwargs):
        if not call_if_callable(request.user.is_authenticated):
            user_ip = get_client_ip(request)
            LOG.info(
                "Unauthenticated user with IP %s attempted to use authenticated method %s.",
                user_ip,
                func.__name__,
            )
            raise PermissionDenied("Login required.")
        return func(request, *args, **kwargs)

    _new_func.__name__ = func.__name__
    _new_func.__doc__ = func.__doc__
    _new_func.__dict__.update(func.__dict__)
    return _new_func


def admin_required(func):
    def _new_func(request, *args, **kwargs):
        if not request.user.is_superuser:
            user_ip = get_client_ip(request)
            username = request.user.username or "*anonymous*"
            LOG.info(
                "User %s with IP %s attempted admin access to method %s.",
                username,
                user_ip,
                func.__name__,
            )
            raise PermissionDenied("Admin only.")
        return func(request, *args, **kwargs)

    _new_func.__name__ = func.__name__
    _new_func.__doc__ = func.__doc__
    _new_func.__dict__.update(func.__dict__)
    return _new_func


def validate_user(func):
    def _new_func(request, user_id, *args, **kwargs):
        if request.user.id != user_id:
            user_ip = get_client_ip(request)
            username = request.user.username or "*anonymous*"
            LOG.info(
                "User %s with IP %s has mismatching id while accessing method %s.",
                username,
                user_ip,
                func.__name__,
            )
            raise SuspiciousOperation("UserID doesn't match logged in user.")
        return func(request, user_id, *args, **kwargs)

    _new_func.__name__ = func.__name__
    _new_func.__doc__ = func.__doc__
    _new_func.__dict__.update(func.__dict__)
    return _new_func


def log_call(function):
    def _new_function(request, *args, **kwargs):
        try:
            argspec = inspect.getargspec(function)
            arg_names = argspec[0][1:]
            known_args = list(zip(arg_names, args))
            unknown_args = list(enumerate(args[len(arg_names):]))
            keyword_args = [ (key, value) for key, value in six.iteritems(kwargs) if (key, value) not in known_args ]

            log = XmlRpcLog()
            log.user = request.user
            log.method = function.__name__
            log.args = str(known_args + unknown_args + keyword_args)
            log.save()
        except:
            pass
        return function(request, *args, **kwargs)

    _new_function.__name__ = function.__name__
    _new_function.__doc__ = function.__doc__
    _new_function.__dict__.update(function.__dict__)
    return _new_function


@decorator_with_args
def log_traceback(function, logdir):
    def _new_function(request, *args, **kwargs):
        try:
            result = function(request, *args, **kwargs)
        except Exception as ex:
            # logdir must be absolute path
            if os.path.abspath(logdir) != logdir:
                raise

            if not os.path.isdir(logdir):
                os.makedirs(logdir)

            # create a file name from function name, date, time and some random characters
            file_name = "%s_%s_%s" % (
                function.__name__,
                datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H-%M-%S"),
                random_string(32),
            )

            # create a file with 0600 perms (log can contain sensitive information like passwords)
            file_path = os.path.join(logdir, file_name)
            fd = os.open(file_path, os.O_CREAT | os.O_WRONLY, 0o600)
            os.write(fd, Traceback().get_traceback())
            os.close(fd)
            raise

        return result

    _new_function.__name__ = function.__name__
    _new_function.__doc__ = function.__doc__
    _new_function.__dict__.update(function.__dict__)
    return _new_function
