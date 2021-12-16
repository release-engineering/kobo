# -*- coding: utf-8 -*-


from django.conf.urls import url
from kobo.hub.models import TASK_STATES
from kobo.hub.views import TaskListView, TaskDetail
import kobo.hub.views
from kobo.django.compat import gettext_lazy as _


urlpatterns = [
    url(r"^$", TaskListView.as_view(), name="task/index"),
    url(r"^(?P<pk>\d+)/$", TaskDetail.as_view(), name="task/detail"),
    url(r"^running/$", TaskListView.as_view(state=(TASK_STATES["FREE"], TASK_STATES["ASSIGNED"], TASK_STATES["OPEN"]), title=_("Running tasks"), order_by=["id"]), name="task/running"),
    url(r"^finished/$", TaskListView.as_view(state=(TASK_STATES["CLOSED"], TASK_STATES["INTERRUPTED"], TASK_STATES["CANCELED"], TASK_STATES["FAILED"]), title=_("Finished tasks"), order_by=["-dt_created", "id"]), name="task/finished"),
    url(r"^(?P<id>\d+)/log/(?P<log_name>.+)$", kobo.hub.views.task_log, name="task/log"),
    url(r"^(?P<id>\d+)/log-json/(?P<log_name>.+)$", kobo.hub.views.task_log_json, name="task/log-json"),
]
