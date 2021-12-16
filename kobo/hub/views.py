# -*- coding: utf-8 -*-

import mimetypes
import os
import six
import locale
from kobo.django.django_version import django_version_ge

try:
    import json
except ImportError:
    import simplejson as json

import django.contrib.auth.views
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.core.exceptions import ImproperlyConfigured
from kobo.django.django_version import django_version_ge
if django_version_ge('1.10.0'):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext
from django.views.generic import RedirectView

from kobo.hub.models import Arch, Channel, Task
from kobo.hub.forms import TaskSearchForm
from kobo.django.views.generic import ExtraDetailView, SearchView
from kobo.django.compat import gettext_lazy as _


# max log size returned in HTML-embedded view
HTML_LOG_MAX_SIZE = getattr(settings, "HTML_LOG_MAX_SIZE", (1024 ** 2) * 2)

# max log size returned in a JSON request
JSON_LOG_MAX_SIZE = getattr(settings, "JSON_LOG_MAX_SIZE", (1024 ** 2) * 8)

# default LogWatcher JS poll interval
LOG_WATCHER_INTERVAL = getattr(settings, "LOG_WATCHER_INTERVAL", 5000)


class UserDetailView(ExtraDetailView):
    model = get_user_model()
    title = _("User detail")
    template_name = "user/detail.html"
    context_object_name = "usr"

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        context['tasks'] = kwargs['object'].task_set.count()
        return context

class DetailViewWithWorkers(ExtraDetailView):
    model = Channel
    template_name = "channel/detail.html"
    context_object_name = "channel"
    title = _("Architecture detail")

    def get_context_data(self, **kwargs):
        context = super(DetailViewWithWorkers, self).get_context_data(**kwargs)
        context["worker_list"] = kwargs["object"].worker_set.order_by("name")
        return context

class ArchDetailView(ExtraDetailView):
    model = Arch
    template_name = "arch/detail.html"
    context_object_name = "arch"
    title = _("Architecture detail")

    def get_context_data(self, **kwargs):
        context = super(ArchDetailView, self).get_context_data(**kwargs)
        context["worker_list"] = kwargs["object"].worker_set.order_by("name")
        return context

class TaskListView(SearchView):
    # TODO: missing kwargs custom queries for backward compatibility
    title = _("All tasks")
    model = Task
    form_class = TaskSearchForm
    template_name = "task/list.html"
    context_object_name = "task_list"
    state = None
    order_by = ['-id']

    def get_form_kwargs(self):
        kwargs = super(TaskListView, self).get_form_kwargs()
        kwargs['state'] = self.state
        kwargs['order_by'] = self.order_by
        return kwargs


class TaskDetail(ExtraDetailView):
    queryset = Task.objects.select_related()
    context_object_name = "task"
    template_name = "task/detail.html"
    title = _("Task detail")

    def get_context_data(self, **kwargs):
        context = super(TaskDetail, self).get_context_data(**kwargs)
        logs = []
        for i in kwargs['object'].logs.list:
            if self.request.user.has_perm('hub.can_see_traceback'):
                logs.append(i)
                continue
            if not os.path.basename(i).startswith("traceback"):
                logs.append(i)
        logs.sort()
        context["logs"] = logs
        context['task_list'] = kwargs['object'].subtasks()
        return context


def _stream_file(file_path, offset=0):
    """Generator that returns 1M file chunks."""
    try:
        f = open(file_path, "rb")
    except IOError:
        return

    f.seek(offset)
    while 1:
        data = f.read(1024 ** 2)
        if not data:
            break
        yield data
    f.close()


def _trim_log(text):
    # break at first line if possible
    nl = text.find('\n')
    if nl > 0:
        subtext = text[nl:]
    else:
        subtext = '\n' + text
    return '<...trimmed, download required for full log>' + subtext


def _streamed_log_response(file_path, offset, as_attachment):
    mimetype = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    try:
        content_len = os.path.getsize(file_path) - offset
    except OSError:
        content_len = 0

    # use _stream_file() instead of passing file object in order to improve performance
    response = StreamingHttpResponse(_stream_file(file_path, offset), content_type=mimetype)
    response["Content-Length"] = content_len

    if as_attachment:
        # set filename to be real filesystem name
        response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)

    return response


def _rendered_log_response(request, task, log_name):
    exts = getattr(settings, "VALID_TASK_LOG_EXTENSIONS", [".log"])
    found = False
    for ext in exts:
        if log_name.endswith(ext):
            found = True
    if not found:
        return HttpResponseForbidden("Can display only specific file types: %s" % ", ".join(exts))

    (content, offset) = task.logs.tail(log_name, HTML_LOG_MAX_SIZE)

    # Add "trimmed" message if tail did not return entire log file.
    if len(content) < offset:
        content = b'<...trimmed, download required for full log>\n' + content

    content = content.decode("utf-8", "replace")

    context = {
        "title": "Task log",
        "offset": offset,
        "task_finished": task.is_finished() and 1 or 0,
        "next_poll": None if task.is_finished() else LOG_WATCHER_INTERVAL,
        "content": content,
        "log_name": log_name,
        "task": task,
        "json_url": reverse("task/log-json", args=[task.id, log_name]),
    }

    return render(request, "task/log.html", context)


def task_log(request, id, log_name):
    """
    IMPORTANT: reverse to 'task/log-json' *must* exist
    """
    if os.path.basename(log_name).startswith("traceback") and not request.user.has_perm('hub.can_see_traceback'):
        return HttpResponseForbidden("You don't have permission to see the traceback.")

    task = get_object_or_404(Task, id=id)

    file_path = task.logs._get_absolute_log_path(log_name)
    if not os.path.isfile(file_path) and not file_path.endswith(".gz"):
        file_path = task.logs._get_absolute_log_path(log_name + ".gz")

    offset = int(request.GET.get("offset", 0))

    request_format = request.GET.get("format")

    if request_format == "raw" or log_name.endswith(".html") or log_name.endswith(".htm"):
        return _streamed_log_response(file_path, offset, as_attachment=(request_format == 'raw'))

    return _rendered_log_response(request, task, log_name)


def task_log_json(request, id, log_name):
    if os.path.basename(log_name).startswith("traceback") and not request.user.is_superuser:
        return HttpResponseForbidden(content_type="application/json")

    task = get_object_or_404(Task, id=id)
    offset = int(request.GET.get("offset", 0))
    content = task.logs.get_chunk(log_name, offset, JSON_LOG_MAX_SIZE + 5)

    if len(content) > JSON_LOG_MAX_SIZE:
        # We immediately have more log content to read
        next_poll = 0
        content = content[:JSON_LOG_MAX_SIZE]
    elif task.is_finished():
        # There is certainly nothing more to read
        next_poll = None
    else:
        # Task is not finished, so there might be more to read,
        # check back soon
        next_poll = LOG_WATCHER_INTERVAL

    if six.PY3:
        content = str(content, encoding=locale.getpreferredencoding())

    result = {
        "new_offset": offset + len(content),
        "task_finished": task.is_finished() and 1 or 0,
        "next_poll": next_poll,
        "content": content,
    }

    return HttpResponse(json.dumps(result), content_type="application/json")

if django_version_ge('1.11.0'):
    class LoginView(django.contrib.auth.views.LoginView):
        template_name = 'auth/login.html'

    class LogoutView(django.contrib.auth.views.LogoutView):
        pass

else:
    def login(request, redirect_field_name=REDIRECT_FIELD_NAME):
        return django.contrib.auth.views.login(request, template_name="auth/login.html", redirect_field_name=redirect_field_name)

    def logout(request, redirect_field_name=REDIRECT_FIELD_NAME):
        return django.contrib.auth.views.logout(request, redirect_field_name=redirect_field_name)


def krb5login(request, redirect_field_name=REDIRECT_FIELD_NAME):
    #middleware = 'django.contrib.auth.middleware.RemoteUserMiddleware'
    middleware = 'kobo.django.auth.middleware.LimitedRemoteUserMiddleware'
    if django_version_ge('1.10.0'):
        middleware_setting = settings.MIDDLEWARE
    else:
        middleware_setting = settings.MIDDLEWARE_CLASSES
    if middleware not in middleware_setting:
        raise ImproperlyConfigured("krb5login view requires '%s' middleware installed" % middleware)
    redirect_to = request.POST.get(redirect_field_name, "")
    if not redirect_to:
        redirect_to = request.GET.get(redirect_field_name, "")
    if not redirect_to:
        redirect_to = reverse("home/index")
    return RedirectView.as_view(url=redirect_to, permanent=True)(request)

