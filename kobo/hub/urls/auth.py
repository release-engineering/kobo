# -*- coding: utf-8 -*-


from django.conf.urls import url
import kobo.hub.views
from kobo.django.django_version import django_version_ge

if django_version_ge('1.11.0'):
    urlpatterns = [
        url(r"^login/$", kobo.hub.views.LoginView.as_view(), name="auth/login"),
        url(r"^krb5login/$", kobo.hub.views.krb5login, name="auth/krb5login"),
        url(r'^logout/$', kobo.hub.views.LogoutView.as_view(), name="auth/logout"),
    ]

else:
    urlpatterns = [
        url(r"^login/$", kobo.hub.views.login, name="auth/login"),
        url(r"^krb5login/$", kobo.hub.views.krb5login, name="auth/krb5login"),
        url(r'^logout/$', kobo.hub.views.logout, name="auth/logout"),
    ]
