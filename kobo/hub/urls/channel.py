# -*- coding: utf-8 -*-

from kobo.django.compat import gettext_lazy as _
from kobo.django.django_version import django_version_ge
if django_version_ge("2.0"):
    from django.urls import re_path as url
    
else:
    from django.conf.urls import url
from kobo.django.views.generic import ExtraListView
from kobo.hub.views import DetailViewWithWorkers
from kobo.hub.models import Channel

urlpatterns = [
    url(r"^$", ExtraListView.as_view(
        queryset=Channel.objects.order_by("name"),
        template_name="channel/list.html",
        context_object_name="channel_list",
        title=_("Channels"),
    ), name="channel/list"),
    url(r"^(?P<pk>\d+)/$", DetailViewWithWorkers.as_view(
        model = Channel,
        template_name = "channel/detail.html",
        context_object_name = "channel",
        title = _("Channel detail"),
    ), name="channel/detail"),
]
