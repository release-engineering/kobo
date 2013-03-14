# -*- coding: utf-8 -*-

from django.conf import settings
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

def _object_list(request, queryset, **kwargs):
    """
    Appends GET variables to the context. Use for paginated searches.
    In settings.py you can set optional parameter PAGINATE_BY which will be
    used as a default value.
    """

    extra_context = kwargs.pop('extra_context', {})

    get_vars = request.GET.copy()
    if "page" in get_vars:
        del get_vars["page"]

    if len(get_vars) > 0:
        extra_context["get_vars"] = "&%s" % get_vars.urlencode()
    else:
        extra_context["get_vars"] = ""

    if not "paginate_by" in kwargs:
        kwargs["paginate_by"] = getattr(settings, "PAGINATE_BY", None)

    class EnhancedListView(ListView):
        def get_context_data(self, **kwargs):
            context = super(EnhancedListView, self).get_context_data(**kwargs)
            context.update(extra_context)
            return context

    kwargs['queryset'] = queryset
    return EnhancedListView.as_view(**kwargs)(request)

class ExtraListView(ListView):
    # pagination
    # filter
    extra_context = {}
    def get_context_data(self, **kwargs):
        context = super(ExtraListView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

def object_list(request, **kwargs):
    return ExtraListView.as_view(**kwargs)(request)

class ExtraDetailView(DetailView):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraDetailView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context
