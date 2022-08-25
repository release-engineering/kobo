# -*- coding: utf-8 -*-


from kobo.django.django_version import django_version_ge
if django_version_ge("2.0"):
    from django.urls import re_path as url
    
else:
    from django.conf.urls import url
from kobo.django.views.generic import ExtraListView, ExtraDetailView
from kobo.hub.models import Worker
from kobo.django.compat import gettext_lazy as _


urlpatterns = [
    url(r"^$", ExtraListView.as_view(
        queryset=Worker.objects.order_by("name"),
        template_name="worker/list.html",
        context_object_name="worker_list",
        title = _("Workers"),
    ), name="worker/list"),
    url(r"^(?P<pk>\d+)/$", ExtraDetailView.as_view(
        queryset=Worker.objects.select_related(),
        template_name="worker/detail.html",
        context_object_name="worker",
        title=_("Worker detail"),
    ), name="worker/detail"),
]
