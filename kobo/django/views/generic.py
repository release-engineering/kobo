# -*- coding: utf-8 -*-


import django.views.generic.list_detail
from django.conf import settings


def object_list(request, queryset, **kwargs):
    """
    Appends GET variables to the context. Use for paginated searches.
    In settings.py you can set optional parameter PAGINATE_BY which will be
    used as a default value.
    """

    kwargs.setdefault("extra_context", {})

    get_vars = request.GET.copy()
    if "page" in get_vars:
        del get_vars["page"]

    if len(get_vars) > 0:
        kwargs["extra_context"]["get_vars"] = "&%s" % get_vars.urlencode()
    else:
        kwargs["extra_context"]["get_vars"] = ""

    if not "paginate_by" in kwargs:
        kwargs["paginate_by"] = getattr(settings, "PAGINATE_BY", None)

    return django.views.generic.list_detail.object_list(request, queryset, **kwargs)
