# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^login/$", "kobo.hub.views.login", name="auth/login"),
    url(r"^krb5login/$", "kobo.hub.views.krb5login", name="auth/krb5login"),
    url(r'^logout/$', 'kobo.hub.views.logout', name="auth/logout"),
)
