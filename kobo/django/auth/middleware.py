from django.contrib.auth.middleware import RemoteUserMiddleware

class LimitedRemoteUserMiddleware(RemoteUserMiddleware):
    '''
    Same behaviour as RemoteUserMiddleware except that it doesn't logout user
    if is already logged in.
    Useful when you have just one authentication powered login page.
    '''
    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated():
            super(LimitedRemoteUserMiddleware, self).process_request(request)
