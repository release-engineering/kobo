# -*- coding: utf-8 -*-


from kobo.django.django_version import django_version_ge
if django_version_ge("2.0"):
    from django.urls import re_path as url
    
else:
    from django.conf.urls import url
import kobo.hub.views

urlpatterns = [
    url(r"^login/$", kobo.hub.views.LoginView.as_view(), name="auth/login"),
    url(r"^krb5login/$", kobo.hub.views.krb5login, name="auth/krb5login"),
    url(r"^oidclogin/$", kobo.hub.views.oidclogin, name="auth/oidclogin"),
    url(r"^tokenoidclogin/$", kobo.hub.views.oidclogin, name="auth/tokenoidclogin"),
    url(r'^logout/$', kobo.hub.views.LogoutView.as_view(), name="auth/logout"),
]
