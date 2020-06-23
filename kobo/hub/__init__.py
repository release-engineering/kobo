# -*- coding: utf-8 -*-


import os

from kobo.exceptions import ImproperlyConfigured
from django.conf import settings
from kobo.django.django_version import django_version_ge


for var in ["XMLRPC_METHODS", "TASK_DIR", "UPLOAD_DIR"]:
    if not hasattr(settings, var):
        raise ImproperlyConfigured("'%s' is missing in project settings. It must be set to run kobo.hub app." % var)


for var in ["TASK_DIR", "UPLOAD_DIR"]:
    dir_path = getattr(settings, var)
    if not os.path.isdir(dir_path):
        try:
            os.makedirs(dir_path)
        except:
            raise ImproperlyConfigured("'%s' doesn't exist and can't be automatically created." % dir_path)
    elif not os.access(dir_path, os.R_OK | os.W_OK | os.X_OK):
        raise ImproperlyConfigured("Invalid permissions on '%s'." % dir_path)


if django_version_ge("1.10.0"):
    middleware_var = "MIDDLEWARE"
else:
    middleware_var = "MIDDLEWARE_CLASSES"

for var, value in [(middleware_var, "kobo.hub.middleware.WorkerMiddleware")]:
    if not hasattr(settings, var) or value not in getattr(settings, var, []):
        raise ImproperlyConfigured("'%s' in '%s' is missing in project settings. It must be set to run kobo.hub app." % (value, var))
