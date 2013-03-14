# -*- coding: utf-8 -*-


from django.utils.translation import ugettext_lazy as _
from django.conf.urls import url, patterns
from kobo.django.views.generic import ExtraListView
from kobo.hub.views import ChannelDetailView
from kobo.hub.models import Channel

urlpatterns = patterns("",
    url(r"^$", ExtraListView.as_view(
        queryset=Channel.objects.order_by("name"),
        template_name="channel/list.html",
        context_object_name="channel_list",
        extra_context={"title": _("Channels")},
    ), name="channel/list"),
    url(r"^(?P<pk>\d+)/$", ChannelDetailView.as_view(), name="channel/detail"),
)
