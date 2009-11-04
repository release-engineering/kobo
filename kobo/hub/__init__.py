# -*- coding: utf-8 -*-


import os

from kobo.exceptions import ImproperlyConfigured
from django.conf import settings


for var in ["XMLRPC_METHODS", "TASK_DIR"]:
    if not hasattr(settings, var):
        raise ImproperlyConfigured("'%s' is missing in project settings. It must be set to run kobo.hub app." % var)


if not os.path.isdir(settings.TASK_DIR):
    try:
        os.makedirs(settings.TASK_DIR)
    except:
        raise ImproperlyConfigured("'%s' doesn't exist and can't be automatically created." % settings.TASK_DIR)
elif not os.access(settings.TASK_DIR, os.R_OK | os.W_OK | os.X_OK):
    raise ImproperlyConfigured("Invalid permissions on '%s'." % settings.TASK_DIR)


for var, value in [("MIDDLEWARE_CLASSES", "kobo.hub.middleware.WorkerMiddleware")]:
    if not hasattr(settings, var) or value not in getattr(settings, var, []):
        raise ImproperlyConfigured("'%s' in '%s' is missing in project settings. It must be set to run kobo.hub app." % (value, var))
