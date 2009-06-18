# -*- coding: utf-8 -*-


from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^$", "kobo.django.upload.views.file_upload"),
)
