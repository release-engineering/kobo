# -*- coding: utf-8 -*-


import django.views.generic.list_detail


def object_list(request, queryset, **kwargs):
    """Appends GET variables to the context. Use for paginated searches."""

    kwargs.setdefault("extra_context", {})

    get_vars = request.GET.copy()
    if "page" in get_vars:
        del get_vars["page"]

    if len(get_vars) > 0:
        kwargs["extra_context"]["get_vars"] = "&%s" % get_vars.urlencode()
    else:
        kwargs["extra_context"]["get_vars"] = ""

    return django.views.generic.list_detail.object_list(request, queryset, **kwargs)
