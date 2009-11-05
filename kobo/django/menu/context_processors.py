# -*- coding: utf-8 -*-


__all__ = (
    "menu_context_processor",
)


def menu_context_processor(request):
    """
    @summary: Context processor for menu object.
    @param request: http request object
    @type request: django.http.HttpRequest
    """
    return {
        "menu": request.menu
    }
