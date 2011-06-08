# -*- coding: utf-8 -*-


import os

from kobo.exceptions import ImproperlyConfigured
from django.conf import settings


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


for var, value in [("MIDDLEWARE_CLASSES", "kobo.hub.middleware.WorkerMiddleware")]:
    if not hasattr(settings, var) or value not in getattr(settings, var, []):
        raise ImproperlyConfigured("'%s' in '%s' is missing in project settings. It must be set to run kobo.hub app." % (value, var))
