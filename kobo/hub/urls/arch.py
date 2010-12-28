# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^$", "kobo.hub.views.arch_list", name="arch/list"),
    url(r"^(?P<id>\d+)/$", "kobo.hub.views.arch_detail", name="arch/detail"),
)
