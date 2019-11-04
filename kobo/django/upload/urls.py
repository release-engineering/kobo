# -*- coding: utf-8 -*-


from django.conf.urls.defaults import url
import kobo.django.upload.views


urlpatterns = [
    url(r"^$", kobo.django.upload.views.file_upload),
]
