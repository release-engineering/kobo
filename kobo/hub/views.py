# -*- coding: utf-8 -*-


import os

import django.contrib.auth.views
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from django.views.generic import RedirectView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from kobo.hub.models import Arch, Channel, Task
from kobo.hub.forms import TaskSearchForm

class UserDetailView(DetailView):
    model = User
    template_name = "user/detail.html"
    context_object_name = "usr"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context['title'] = _("User detail")
        context['tasks'] = kwargs['object'].task_set.count()
        return context

class ChannelDetailView(DetailView):
    model = Channel
    template_name = "channel/detail.html"
    context_object_name = "channel"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["title"] = _("Architecture detail")
        context["worker_list"] = kwargs["object"].worker_set.order_by("name")
        return context

class ArchDetailView(DetailView):
    model = Arch
    template_name = "arch/detail.html"
    context_object_name = "arch"

    def get_context_data(self, **kwargs):
        context = super(DetailView, self).get_context_data(**kwargs)
        context["title"] = _("Architecture detail")
        context["worker_list"] = kwargs["object"].worker_set.order_by("name"),
        return context


class TaskListView(ListView):
    template_name = "task/list.html"
    context_object_name = "task_list"
    title = _("Tasks")
    state = None
    order_by = None
    paginate_by = 50

    def get_queryset(self):
        q = TaskSearchForm(self.request.GET).get_query(self.request)
        q &= Q(parent__isnull=True)
        if self.state is not None:
            q &= Q(state__in=self.state)
        if self.kwargs:
            q &= Q(self.kwargs)
        order_by = self.order_by or ["-id"]
        return Task.objects.filter(q).order_by(*order_by).defer("result", "args").select_related("owner", "worker")

    def get_context_data(self, **kwargs):
        context = super(TaskListView, self).get_context_data(**kwargs)
        context["search_form"] = TaskSearchForm(self.request.GET)
        return context


class TaskDetail(DetailView):
    queryset = Task.objects.select_related()
    context_object_name = "task"
    template_name = "task/detail.html"
    title = _("Task detail")

    def get_context_data(self, **kwargs):
        context = super(TaskDetail, self).get_context_data(**kwargs)
        logs = []
        for i in kwargs['object'].logs.list:
            if self.request.user.is_superuser:
                logs.append(i)
                continue
            if not os.path.basename(i).startswith("traceback"):
                logs.append(i)
        context["logs"] = logs
        return context


def _stream_file(file_path, offset=0):
    """Generator that returns 1M file chunks."""
    try:
        f = open(file_path, "r")
    except IOError:
        return

    f.seek(offset)
    while 1:
        data = f.read(1024 ** 2)
        if not data:
            break
        yield data
    f.close()


def task_log(request, id, log_name):
    """
    IMPORTANT: reverse to 'task/log-json' *must* exist
    """
    if os.path.basename(log_name).startswith("traceback") and not request.user.is_superuser:
        return HttpResponseForbidden("Traceback is available only for superusers.")

    task = get_object_or_404(Task, id=id)

    file_path = task.logs._get_absolute_log_path(log_name)
    if not os.path.isfile(file_path) and not file_path.endswith(".gz"):
        file_path = task.logs._get_absolute_log_path(log_name + ".gz")

    import mimetypes
    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    offset = int(request.GET.get("offset", 0))
    try:
        content_len = os.path.getsize(file_path) - offset
    except OSError:
        content_len = 0

    if request.GET.get("format") == "raw":
        # use _stream_file() instad of passing file object in order to improve performance
        response = HttpResponse(_stream_file(file_path, offset), mimetype=mimetype)

        response["Content-Length"] = content_len
        # set filename to be real filesystem name
        response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)
        return response

    if log_name.endswith(".html") or log_name.endswith(".htm"):
        # use _stream_file() instad of passing file object in order to improve performance
        response = HttpResponse(_stream_file(file_path, offset), mimetype=mimetype)
        response["Content-Length"] = content_len
        return response

    exts = getattr(settings, "VALID_TASK_LOG_EXTENSIONS", [".log"])
    found = False
    for ext in exts:
        if log_name.endswith(ext):
            found = True
    if not found:
        return HttpResponseForbidden("Can display only specific file types: %s" % ", ".join(exts))

    content = task.logs[log_name][offset:]
    content = content.decode("utf-8", "replace")
    context = {
        "title": "Task log",
        "offset": offset + content_len + 1,
        "task_finished": task.is_finished() and 1 or 0,
        "content": content,
        "log_name": log_name,
        "task": task,
        "json_url": reverse("task/log-json", args=[id, log_name]),
    }

    return render_to_response("task/log.html", context, context_instance=RequestContext(request))


def task_log_json(request, id, log_name):
    if os.path.basename(log_name).startswith("traceback") and not request.user.is_superuser:
        return HttpResponseForbidden(mimetype="application/json")

    task = get_object_or_404(Task, id=id)
    offset = int(request.GET.get("offset", 0))
    content = task.logs[log_name][offset:]

    result = {
        "new_offset": offset + len(content),
        "task_finished": task.is_finished() and 1 or 0,
        "content": content,
    }

    return HttpResponse(simplejson.dumps(result), mimetype="application/json")


def login(request, redirect_field_name=REDIRECT_FIELD_NAME):
    return django.contrib.auth.views.login(request, template_name="auth/login.html", redirect_field_name=redirect_field_name)


def krb5login(request, redirect_field_name=REDIRECT_FIELD_NAME):
    #middleware = 'django.contrib.auth.middleware.RemoteUserMiddleware'
    middleware = 'kobo.django.auth.middleware.LimitedRemoteUserMiddleware'
    if middleware not in settings.MIDDLEWARE_CLASSES:
        raise ImproperlyConfigured("krb5login view requires '%s' middleware installed" % middleware)
    redirect_to = request.REQUEST.get(redirect_field_name, "")
    if not redirect_to:
        redirect_to = reverse("home/index")
    return RedirectView.as_view(url=redirect_to)(request)
    

def logout(request, redirect_field_name=REDIRECT_FIELD_NAME):
    return django.contrib.auth.views.logout(request, redirect_field_name=redirect_field_name)
