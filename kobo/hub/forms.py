# -*- coding: utf-8 -*-


import django.forms as forms
from django.db.models import Q
from kobo.django.helpers import call_if_callable
from kobo.hub.models import Task


class TaskSearchForm(forms.Form):
    search  = forms.CharField(required=False)
    my  = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.state = kwargs.pop('state', None)
        self.order_by = kwargs.pop('order_by', ['-id'])
        return super(TaskSearchForm, self).__init__(*args, **kwargs)

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]
        my = self.cleaned_data["my"]

        query = Q()

        if search:
            query |= Q(method__icontains=search)
            query |= Q(owner__username__icontains=search)
            query |= Q(label__icontains=search)

        if my and call_if_callable(request.user.is_authenticated):
            query &= Q(owner=request.user)

        if self.state is not None:
            query &= Q(state__in=self.state)
        #if self.kwargs:
        #    query &= Q(self.kwargs)
        return Task.objects.filter(parent__isnull=True).filter(query).order_by(*self.order_by).defer("result", "args").select_related("owner", "worker")
