# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^arch/$", "kobo.hub.views.arch_list", name="arch/list"),
    url(r"^arch/(?P<id>\d+)/$", "kobo.hub.views.arch_detail", name="arch/detail"),
    url(r"^channel/$", "kobo.hub.views.channel_list", name="channel/list"),
    url(r"^channel/(?P<id>\d+)/$", "kobo.hub.views.channel_detail", name="channel/detail"),
    url(r"^user/$", "kobo.hub.views.user_list", name="user/list"),
    url(r"^user/(?P<id>\d+)/$", "kobo.hub.views.user_detail", name="user/detail"),
    url(r"^worker/$", "kobo.hub.views.worker_list", name="worker/list"),
    url(r"^worker/(?P<id>\d+)/$", "kobo.hub.views.worker_detail", name="worker/detail"),
)
