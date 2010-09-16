# -*- coding: utf-8 -*-


import django.forms as forms
from django.db.models import Q


class TaskSearchForm(forms.Form):
    search  = forms.CharField(required=False)
    my  = forms.BooleanField(required=False)

    def get_query(self, request):
        self.is_valid()
        search = self.cleaned_data["search"]
        my = self.cleaned_data["my"]

        query = Q()

        if search:
            query |= Q(method__icontains=search)
            query |= Q(owner__username__icontains=search)

        if my and request.user.is_authenticated():
            query &= Q(owner=request.user)

        return query
