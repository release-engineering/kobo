# -*- coding: utf-8 -*-


from django.contrib.auth import get_user_model
from kobo.django.django_version import django_version_ge
if django_version_ge("2.0"):
    from django.urls import re_path as url
    
else:
    from django.conf.urls import url
from kobo.django.views.generic import UserListView
from kobo.hub.views import UserDetailView
from kobo.django.compat import gettext_lazy as _


urlpatterns = [
    url(r"^$", UserListView.as_view(
        queryset=get_user_model().objects.order_by("username"),
        template_name="user/list.html",
        context_object_name="usr_list",
        title = _('Users'),
    ), name="user/list"),
    url(r"^(?P<pk>\d+)/$", UserDetailView.as_view(), name="user/detail"),
]
