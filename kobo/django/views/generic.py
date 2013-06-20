# -*- coding: utf-8 -*-

import warnings
from django.conf import settings
from django.views.generic.edit import ProcessFormView, FormMixin
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

class ExtraListView(ListView):
    paginate_by = getattr(settings, "PAGINATE_BY", None)
    extra_context = None
    title = None

    def get_context_data(self, **kwargs):
        context = super(ExtraListView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            context.update(self.extra_context)
        if self.title is not None:
            context['title'] = self.title
        return context

class ExtraDetailView(DetailView):
    extra_context = None
    title = None

    def get_context_data(self, **kwargs):
        context = super(ExtraDetailView, self).get_context_data(**kwargs)
        if self.extra_context is not None:
            context.update(self.extra_context)
        if self.title is not None:
            context['title'] = self.title
        return context

class SearchView(ExtraListView, ProcessFormView, FormMixin):
    """
    Appends GET variables to the context. Used for paginated searches.
    In settings.py you can set optional parameter PAGINATE_BY which will be
    used as a default value.

    Useful fields:
        form_class - form_class is expected that it implements get_query(request)
                     method which returns queryset for displaying in list
    """
    object_list = []

    def form_invalid(self, form):
        self.queryset = []
        return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        self.queryset = form.get_query(self.request)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        kwargs['object_list'] = self.get_queryset()
        context = super(SearchView, self).get_context_data(**kwargs)

        get_vars = self.request.GET.copy()
        if "page" in get_vars:
            del get_vars["page"]
        if len(get_vars) > 0:
            get_vars = "&%s" % get_vars.urlencode()
        else:
            get_vars = ""
        context['get_vars'] = get_vars
        return context

def object_list(request, **kwargs):
    warnings.warn('object_list is deprecated, please use ExtraListView or SearchView in future.')
    return SearchView.as_view(**kwargs)(request)
