# -*- coding: utf-8 -*-


import kobo.hub.models as models
from kobo.django.xmlrpc.decorators import admin_required, login_required


__all__ = (
    "shutdown_worker",
    "task_info",
    "get_tasks",
    "cancel_task",
    "resubmit_task",
    "list_workers",
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
