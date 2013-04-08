# -*- coding: utf-8 -*-

import warnings
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

class ExtraListView(ListView):
    # pagination
    # filter
    extra_context = {}
    def get_context_data(self, **kwargs):
        context = super(ExtraListView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

def object_list(request, **kwargs):
    warnings.warn('object_list is deprecated, please use ExtraListView in future.')
    return ExtraListView.as_view(**kwargs)(request)

class ExtraDetailView(DetailView):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraDetailView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context
