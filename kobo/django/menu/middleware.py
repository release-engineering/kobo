# -*- coding: utf-8 -*-

from kobo.django.menu import menu


__all__ = (
    "MenuMiddleware",
)


class LazyMenu(object):
    """
    @summary: Cached menu object
    """
    def __get__(self, request, obj_type=None):
        if not hasattr(request, "_cached_menu"):
            request._cached_menu = menu.setup(request)
        return request._cached_menu


class MenuMiddleware():
    """
    @summary: Middleware for menu object.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        return response

    def process_request(self, request):
        """
        @summary: Adds menu to request object
        @param request: http request object
        @type request: django.http.HttpRequest
        """
        request.__class__.menu = LazyMenu()
