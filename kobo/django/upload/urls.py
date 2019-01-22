# -*- coding: utf-8 -*-


from django.conf.urls.defaults import url


urlpatterns = [
    url(r"^$", "kobo.django.upload.views.file_upload"),
]
