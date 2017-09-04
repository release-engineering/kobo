# -*- coding: utf-8 -*-


from django.conf.urls.defaults import patterns, url


urlpatterns = patterns("",
    url(r"^$", "kobo.django.upload.views.file_upload"),
)
