# -*- coding: utf-8 -*-


from django.conf.urls import url
from django.utils.translation import ugettext_lazy as _
from kobo.django.views.generic import ExtraListView, ExtraDetailView
from kobo.hub.models import Worker


urlpatterns = [
    url(r"^$", ExtraListView.as_view(
        queryset=Worker.objects.order_by("name"),
        template_name="worker/list.html",
        context_object_name="worker_list",
        title = _("Workers"),
    ), name="worker/list"),
    url(r"^(?P<pk>\d+)/$", ExtraDetailView.as_view(
        queryset=Worker.objects.select_related(),
        template_name="worker/detail.html",
        context_object_name="worker",
        title=_("Worker detail"),
    ), name="worker/detail"),
]
