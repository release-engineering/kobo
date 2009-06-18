from kobo.exceptions import ImproperlyConfigured
from django.conf import settings


var = 'XMLRPC_METHODS'
if not hasattr(settings, var):
    raise ImproperlyConfigured("Variable '%s' is needed to run kobo.hub app." % var)


var = 'MIDDLEWARE_CLASSES'
middleware = 'kobo.hub.middleware.WorkerMiddleware'
for var,value in [
    ('MIDDLEWARE_CLASSES','kobo.hub.middleware.WorkerMiddleware'),
    ('AUTHENTICATION_BACKENDS', 'kobo.django.auth.krb5.Krb5Backend'),]:
    if not hasattr(settings, var) or value not in getattr(settings, var, []):
        raise  ImproperlyConfigured("%s must be set in %s to run kobo.hub app." % (value,var))

