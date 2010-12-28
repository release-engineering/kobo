# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^$", "kobo.hub.views.user_list", name="user/list"),
    url(r"^(?P<id>\d+)/$", "kobo.hub.views.user_detail", name="user/detail"),
)
