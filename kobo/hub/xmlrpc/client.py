# -*- coding: utf-8 -*-


from kobo.django.django_version import django_version_ge
if django_version_ge('1.10.0'):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from kobo.hub import models
from kobo.django.xmlrpc.decorators import admin_required, login_required


__all__ = (
    "enable_worker",
    "disable_worker",
    "get_worker_info",
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
    """shutdown_worker(worker_name, kill): None

    Send shutdown request to a worker.
    If kill argument is set to True, kill worker immediately,
    otherwise wait until all tasks assigned to the are finished.
    """
    return models.Task.create_shutdown_task(request.user.username, worker_name, kill=kill)


@admin_required
def enable_worker(request, worker_name):
    """enable_worker(worker_name): none
    """
    models.Worker.objects.filter(name=worker_name).update(enabled=True)


@admin_required
def disable_worker(request, worker_name):
    """disable_worker(worker_name, kill): None
    """
    models.Worker.objects.filter(name=worker_name).update(enabled=False)

def get_worker_info(request, worker_name):
    try:
        return models.Worker.objects.get(name=worker_name).export()
    except models.Worker.DoesNotExist:
        return {}

def task_info(request, task_id, flat=False):
    """task_info(task_id, flat=False): dict or None"""
    task = models.Task.objects.get(id=task_id)
    return task.export(flat=flat)


def get_tasks(request, task_id_list, state_list=None):
    """get_tasks(task_id_list): list

    @param task_id_list: list of task ids, can be empty, then all tasks are
    retrieved
    @type task_id_list: [int]
    @param state_list: task state ids by which task_id_list should be
    filtered
    @type: [int]
    @return: list of task_info dicts
    @rtype: list
    """

    if task_id_list:
        tasks = models.Task.objects.filter(id__in=task_id_list)
    else:
        tasks = models.Task.objects.all()
    if state_list:
        tasks = tasks.filter(state__in=state_list)
    return [i.export(flat=True) for i in tasks]


@login_required
def cancel_task(request, task_id):
    try:
        task = models.Task.objects.get(id=task_id)
    except ObjectDoesNotExist:
        return "Specified task %s does not exist." % task_id
    return task.cancel_task(user=request.user)


@login_required
def resubmit_task(request, task_id, force=False, priority=None):
    """Resubmit a failed task and return new task_id."""
    task = models.Task.objects.get(id=task_id)
    return task.resubmit_task(request.user, force, priority)


def list_workers(request, enabled=True):
    """
    Get a list of workers.

    @param enabled: filter workers.
    @return: list of workers
    @rtype: list
    """
    return sorted([worker.name for worker in models.Worker.objects.filter(enabled=enabled)])


@admin_required
def create_task(request, kwargs):
    """
    Create a new task which is either brand new or based on existing one.
    This call can be invoked only by superuser.

    @param kwargs: task attributes: owner_name, label, method, args, comment, parent_id,
                   worker_name, arch_name, channel_name, timeout, priority, weight, exclusive
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
    if str(request.META["SERVER_PORT"]) == "443":
        prefix = "https://"
    else:
        prefix = "http://"

    # use HTTP_HOST (address can point to a virtual host)
    # if address points to localhost, use SERVER_NAME in order to make link globally valid
    server_name = request.META["HTTP_HOST"]
    if server_name in ("localhost", "localhost.localdomain"):
        server_name = request.META["SERVER_NAME"]

    return prefix + server_name + reverse("task/detail", args=[task_id])
