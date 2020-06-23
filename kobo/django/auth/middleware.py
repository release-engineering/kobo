from django.contrib.auth.middleware import RemoteUserMiddleware
from kobo.django.django_version import django_version_ge
if django_version_ge('1.10.0'):
    from django.utils.deprecation import MiddlewareMixin

from kobo.django.helpers import call_if_callable

class LimitedRemoteUserMiddleware(RemoteUserMiddleware, MiddlewareMixin if django_version_ge('1.10.0') else object):
    '''
    Same behaviour as RemoteUserMiddleware except that it doesn't logout user
    if is already logged in.
    Useful when you have just one authentication powered login page.
    '''
    def process_request(self, request):
        if not hasattr(request, 'user') or not call_if_callable(request.user.is_authenticated):
            super(LimitedRemoteUserMiddleware, self).process_request(request)
