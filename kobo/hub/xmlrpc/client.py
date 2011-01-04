# -*- coding: utf-8 -*-


from django.core.urlresolvers import reverse

import kobo.hub.models as models
from kobo.django.xmlrpc.decorators import admin_required, login_required


__all__ = (
    "shutdown_worker",
    "task_info",
    "get_tasks",
    "cancel_task",
    "resubmit_task",
    "list_workers",
    "create_task",
    "task_url",
)


@admin_required
def shutdown_worker(request, worker_name, kill=False):
    """shutdown(worker_name, kill): None

    Send shutdown request to a worker.
    If kill argument is set to True, kill worker immediately,
    otherwise wait until all tasks assigned to the are finished.
    """
    return models.Task.create_shutdown_task(request.user.username, worker_name, kill=kill)


def task_info(request, task_id, flat=False):
    """task_info(task_id, flat=False): dict or None"""
    task = models.Task.objects.get(id=task_id)
    return task.export(flat=flat)


def get_tasks(request, task_id_list):
    """get_tasks(task_id_list): list

    @param task_id_list: list of task ids
    @type task_id_list: [int]
    @return: list of task_info dicts
    @rtype: list
    """

    return [ i.export(flat=True) for i in models.Task.objects.filter(id__in=task_id_list) ]


@login_required
def cancel_task(request, task_id):
    task = models.Task.objects.get(id=task_id)
    return task.cancel_task(user=request.user)


@login_required
def resubmit_task(request, task_id):
    """Resubmit a failed task and return new task_id."""
    task = models.Task.objects.get(id=task_id)
    return task.resubmit_task(request.user)


def list_workers(request, enabled=True):
    """(): [string]"""
    return sorted([ worker.name for worker in models.Worker.objects.filter(enabled=enabled) ])


@admin_required
def create_task(request, kwargs):
    """
    Create a new task which is either brand new or based on existing one.
    This call can be invoked only by superuser.

    @param kwargs: task attributes: owner_name, label, method, args, comment, parent_id, worker_name, arch_name, channel_name, timeout, priority, weight, exclusive
                   when task_id is set, the task is used as a template for the new one
    @type kwargs: dict
    @return: task id
    @rtype: int
    """

    old_task_id = kwargs.pop("task_id", None)
    if old_task_id is not None:
        old_task = models.Task.objects.get(id=old_task_id)
        return old_task.clone_task(request.user, **kwargs)

    kwargs.setdefault("label", "")
    kwargs["resubmitted_by"] = request.user
    kwargs["resubmitted_from"] = None
    return models.Task.create_task(**kwargs)


def task_url(request, task_id):
    """
    Get a task URL.

    @param task_id: task ID
    @type  task_id: int
    @return: task URL
    @rtype:  str
    """
    prefix = request.META["SERVER_PORT"] == 443 and "https://" or "http://"

    # use HTTP_HOST (address can point to a virtual host)
    # if address points to localhost, use SERVER_NAME in order to make link globally valid
    server_name = request.META["HTTP_HOST"]
    if server_name in ("localhost", "localhost.localdomain"):
        server_name = request.META["SERVER_NAME"]

    return prefix + server_name + reverse("task/detail", args=[task_id])
