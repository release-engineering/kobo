# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^$", "kobo.hub.views.channel_list", name="channel/list"),
    url(r"^(?P<id>\d+)/$", "kobo.hub.views.channel_detail", name="channel/detail"),
)
