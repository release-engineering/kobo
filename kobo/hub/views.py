# -*- coding: utf-8 -*-


import os

import django.contrib.auth.views
import django.views.generic.simple
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_detail
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import simplejson
from django.db.models import Q

from kobo.django.views.generic import object_list
from kobo.hub.models import Task, Worker, Channel, Arch
from kobo.hub.forms import TaskSearchForm


def user_list(request):
    args = {
        "queryset": User.objects.order_by("username"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "user/list.html",
        "template_object_name": "usr",
        "extra_context": {
            "title": "Users",
        }
    }

    return object_list(request, **args)


def user_detail(request, id):
    user = get_object_or_404(User, id=id)
    args = {
        "queryset": User.objects,
        "object_id": id,
        "template_object_name": "usr",
        "template_name": "user/detail.html",
        "extra_context": {
            "title": "User detail",
            "tasks": Task.objects.filter(owner=user).count(),
        }
    }

    return object_detail(request, **args)


def worker_list(request):
    args = {
        "queryset": Worker.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "worker/list.html",
        "template_object_name": "worker",
        "extra_context": {
            "title": "Workers",
        }
    }

    return object_list(request, **args)


def worker_detail(request, id):
    args = {
        "queryset": Worker.objects.select_related(),
        "object_id": id,
        "template_object_name": "worker",
        "template_name": "worker/detail.html",
        "extra_context": {
            "title": "Worker detail",
        }
    }

    return object_detail(request, **args)


def channel_list(request):
    args = {
        "queryset": Channel.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "channel/list.html",
        "template_object_name": "channel",
        "extra_context": {
            "title": "Channels",
        }
    }

    return object_list(request, **args)


def channel_detail(request, id):
    channel = get_object_or_404(Channel, id=id)
    args = {
        "queryset": Channel.objects,
        "object_id": id,
        "template_object_name": "channel",
        "template_name": "channel/detail.html",
        "extra_context": {
            "title": "Channel detail",
            "worker_list": Worker.objects.filter(channels__name=channel.name),
        }
    }

    return object_detail(request, **args)


def arch_list(request):
    args = {
        "queryset": Arch.objects.order_by("name"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "arch/list.html",
        "template_object_name": "arch",
        "extra_context": {
            "title": "Arches",
        }
    }

    return object_list(request, **args)


def arch_detail(request, id):
    arch = get_object_or_404(Arch, id=id)
    args = {
        "queryset": Arch.objects,
        "object_id": id,
        "template_object_name": "arch",
        "template_name": "arch/detail.html",
        "extra_context": {
            "title": "Arch detail",
            "worker_list": Worker.objects.filter(arches__name=arch.name),
        }
    }

    return object_detail(request, **args)


def task_list(request, state, title="Tasks"):
    search_form = TaskSearchForm(request.GET)

    if state is None:
        state_q = Q()
    else:
        state_q = Q(state__in=state)

    args = {
        "queryset": Task.objects.filter(state_q, parent__isnull=True).filter(search_form.get_query(request)).order_by("-dt_finished", "id").defer("result", "args").select_related("owner", "worker"),
        "allow_empty": True,
        "paginate_by": 50,
        "template_name": "task/list.html",
        "template_object_name": "task",
        "extra_context": {
            "title": title,
            "search_form": search_form,
        }
    }

    return object_list(request, **args)


def task_detail(request, id):
    task = get_object_or_404(Task, id=id)

    logs = []
    for i in task.logs.list:
        if request.user.is_superuser:
            logs.append(i)
            continue
        if not os.path.basename(i).startswith("traceback"):
            logs.append(i)
    logs.sort(lambda x, y: cmp(os.path.split(x), os.path.split(y)))

    args = {
        "queryset": Task.objects.select_related(),
        "object_id": id,
        "template_object_name": "task",
        "template_name": "task/detail.html",
        "extra_context": {
            "title": "Task detail",
            "task_list": task.subtasks(),
            "logs": logs,
        },
    }

    return object_detail(request, **args)


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
        response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(log_name)
        return response

    if not log_name.endswith(".log"):
        return HttpResponseForbidden("Can display only logs.")

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
    middleware = "kobo.django.auth.krb5.Krb5AuthenticationMiddleware"
    if middleware not in settings.MIDDLEWARE_CLASSES:
        raise ImproperlyConfigured("krb5login view requires '%s' middleware installed" % middleware)
    redirect_to = request.REQUEST.get(redirect_field_name, "")
    if not redirect_to:
        redirect_to = reverse("home/index")
    return django.views.generic.simple.redirect_to(request, url=redirect_to)
    

def logout(request, redirect_field_name=REDIRECT_FIELD_NAME):
    return django.contrib.auth.views.logout(request, redirect_field_name=redirect_field_name)
