# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^$", "kobo.hub.views.worker_list", name="worker/list"),
    url(r"^(?P<id>\d+)/$", "kobo.hub.views.worker_detail", name="worker/detail"),
)
