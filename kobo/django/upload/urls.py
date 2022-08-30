# -*- coding: utf-8 -*-

from kobo.django.django_version import django_version_ge
if django_version_ge("2.0"):
    from django.urls import re_path as url
    
else:
    from django.conf.urls import url
import kobo.django.upload.views


urlpatterns = [
    url(r"^$", kobo.django.upload.views.file_upload),
]
