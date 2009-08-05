from kobo.exceptions import ImproperlyConfigured
from django.conf import settings


for var in ["XMLRPC_METHODS"]:
    if not hasattr(settings, var):
        raise ImproperlyConfigured("'%s' must be set to run kobo.hub app." % var)


for var, value in [("MIDDLEWARE_CLASSES", "kobo.hub.middleware.WorkerMiddleware")]:
    if not hasattr(settings, var) or value not in getattr(settings, var, []):
        raise ImproperlyConfigured("%s must be set in %s to run kobo.hub app." % (value, var))
