# -*- coding: utf-8 -*-

import os
import sys
import datetime
import gzip

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import models, connection, transaction
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

import kobo.django.fields
from kobo.client.constants import *
from kobo.shortcuts import random_string, read_from_file, save_to_file, run


def dump_dict(**kwargs):
    """Serialize args dictionary to a json dump."""
    return simplejson.dumps(kwargs)


def load_dict(dump):
    """Deserialize a json dump to dictionary."""
    return simplejson.loads(dump)


class Arch(models.Model):
    """Model for hub_arch table."""
    name        = models.CharField(max_length=16, unique=True, help_text=_("i386, ia64, ..."))
    pretty_name = models.CharField(max_length=64, unique=True, help_text=_("i386, Itanium, ..."))


    class Meta:
        ordering = ("name", )
        verbose_name_plural = "arches"


    def __unicode__(self):
        return u"%s" % self.name


    def export(self):
        """Export data for xml-rpc."""
        return {
            "id": self.id,
            "name": self.name,
            "pretty_name": self.pretty_name,
        }


    @property
    def worker_count(self):
        if self.id is None:
            return 0
        return Worker.objects.filter(arches__id=self.id).count()


class Channel(models.Model):
    """Model for hub_channel table."""
    name        = models.CharField(max_length=128, help_text=_("Channel name"))


    def __unicode__(self):
        return u"%s" % self.name


    def export(self):
        """Export data for xml-rpc."""
        return {
            "id": self.id,
            "name": self.name,
        }


    @property
    def worker_count(self):
        if self.id is None:
            return 0
        return Worker.objects.filter(channels__id=self.id).count()


class WorkerManager(models.Manager):
    """Custom query manager for Worker model."""

    def enabled(self):
        """Return all enabled workers."""
        return self.filter(enabled=True)


    def ready(self):
        """Return all enabled workers which are ready."""
        return self.filter(enabled=True, ready=True)


class Worker(models.Model):
    """Model for the hub_worker table."""
    worker_key          = models.CharField(max_length=255, unique=True, blank=True, help_text=_("Worker authentication key.<br />Leave blank to generate new key."))
    name                = models.CharField(max_length=128, unique=True, help_text=_("Worker hostname."))
    arches              = models.ManyToManyField(Arch, help_text=_("Supported architectures"))
    channels            = models.ManyToManyField(Channel)
    enabled             = models.BooleanField(default=True, help_text=_("Enabled workers are allowed to process tasks."))
    max_load            = models.PositiveIntegerField(blank=True, default=1, help_text=_("Maximum allowed load (sum of task weights)."))
    max_tasks           = models.PositiveIntegerField(blank=True, default=0, help_text=_("Maximum assigned tasks. (0 = no limit)"))

    # redundant fields to improve performance
    ready               = models.BooleanField(default=True, help_text=_("Is the worker ready to take new tasks?<br />This is a generated field."))
    task_count          = models.PositiveIntegerField(blank=True, default=0, help_text=_("Count of processed tasks.<br />This is a generated field."))
    current_load        = models.PositiveIntegerField(blank=True, default=0, help_text=_("Sum of task weights.<br />This is a generated field."))

    # override default *objects* Manager
    objects = WorkerManager()


    def __unicode__(self):
        return u"%s" % self.name


    def save(self, *args, **kwargs):
        # precompute task count, current load and ready
        tasks = Task.objects.running().filter(worker=self)
        self.task_count = tasks.count()
        self.current_load = sum(( task.weight for task in tasks if not task.waiting ))
        self.ready = self.enabled and (self.current_load < self.max_load and self.task_count < 3*self.max_load)

        while not self.worker_key:
            # if worker_key is empty, generate a new one
            key = random_string(64)
            if Worker.objects.filter(worker_key=key).count() == 0:
                self.worker_key = key
        super(self.__class__, self).save(*args, **kwargs)


    def export(self):
        """Export data for xml-rpc."""
        return {
            "id": self.id,
            "name": self.name,
            "arches": [ i.export() for i in self.arches.all() ],
            "channels": [ i.export() for i in self.channels.all() ],
            "enabled": self.enabled,
            "max_load": self.max_load,
            "ready": self.ready,
            "task_count": self.task_count,
            "current_load": self.current_load,

            # Add the hub version.
            # This can be used for taskd compatibility checking everytime a worker_info is updated.
            "version": self._get_version(),
        }


    def _get_version(self):
        """Return hub version or None (if settings.VERSION is not set)."""
        return getattr(settings, "VERSION", None)


    def running_tasks(self):
        """Return list of running tasks on this worker."""
        return Task.objects.running().filter(worker=self)


    def assigned_tasks(self):
        """Return list of assigned tasks to this worker."""
        return Task.objects.assigned().filter(worker=self)


    def update_worker(self, enabled, ready, task_count):
        """Update worker attributes. Return worker_info.

        Update only if data provided from a worker differs.
        """
        if (self.enabled, self.ready, self.task_count) != (enabled, ready, task_count):
            self.save()
        return self.export()


class TaskManager(models.Manager):
    """Custom query manager for Task model."""

    def get_query_set(self):
        """Redefine default query set to exclude archived tasks."""
        return models.Manager.get_query_set(self).filter(archive=False)

    def get_and_verify(self, task_id, worker):
        return self.get(id=task_id, worker=worker)

    def running(self):
        """Return list of assigned or opened tasks."""
        return self.filter(state__in=(TASK_STATES["ASSIGNED"], TASK_STATES["OPEN"])).order_by("-exclusive", "id")

    def free(self):
        """Return list of free tasks."""
        return self.filter(state=TASK_STATES["FREE"]).order_by("-exclusive", "id")

    def assigned(self):
        """Return list of assigned tasks."""
        return self.filter(state=TASK_STATES["ASSIGNED"]).order_by("-exclusive", "id")

    def opened(self):
        """Return list of opened tasks."""
        return self.filter(state=TASK_STATES["OPEN"]).order_by("-exclusive", "id")

    def closed(self):
        """Return list of closed tasks."""
        return self.filter(state=TASK_STATES["CLOSED"]).order_by("-exclusive", "id")

    def canceled(self):
        """Return list of canceled tasks."""
        return self.filter(state=TASK_STATES["CANCELED"]).order_by("-exclusive", "id")

    def failed(self):
        """Return list of failed tasks."""
        return self.filter(state=TASK_STATES["FAILED"]).order_by("-exclusive", "id")

    def interrupted(self):
        """Return list of interrupted tasks."""
        return self.filter(state=TASK_STATES["INTERRUPTED"]).order_by("-exclusive", "id")

    def timeout(self):
        """Return list of tasks killed on a timeout."""
        return self.filter(state=TASK_STATES["TIMEOUT"]).order_by("-exclusive", "id")

    def created(self):
        """Return list of created tasks."""
        return self.filter(state=TASK_STATES["CREATED"]).order_by("-exclusive", "id")


class TaskLogs(object):
    """Task log wrapper."""
    __slots__ = (
        "cache",   # log cache
        "changed", # changed logs, will be written on save()
        "task",
    )


    def __init__(self, task_obj):
        self.cache = {}
        self.changed = {}
        self.task = task_obj


    def _get_absolute_log_path(self, name):
        task_dir = self.task.task_dir(self.task.id)
        log_path = os.path.abspath(os.path.join(self.task.task_dir(), name))
        if not log_path.startswith(task_dir):
            # make sure log is under task_dir
            raise RuntimeError("Invalid log abspath.")
        return log_path


    def _get_relative_log_path(self, name):
        log_path = os.path.normpath(name)
        if log_path.startswith(".."):
            raise RuntimeError("Invalid log normpath.")
        return log_path


    def __getitem__(self, name):
        name = self._get_relative_log_path(name)
        if name not in self.cache:
            # task.id is still not set. Return empty string.
            if self.task.id is None:
                return ""

            log_path = self._get_absolute_log_path(name)
            if os.path.isfile(log_path):
                self.cache[name] = "\n".join(read_from_file(log_path))
            elif os.path.isfile(log_path + ".gz"):
                fo = gzip.open(log_path + ".gz", "rb")
                self.cache[name] = fo.read()
                fo.close()
            else:
                self.cache[name] = ""
            self.changed[name] = False

        return self.cache[name]


    def __setitem__(self, name, value):
        name = self._get_relative_log_path(name)
        self.cache[name] = value
        self.changed[name] = True


    def save(self):
        for log in self.cache:
            if not self.changed.get(log, True):
                continue
            log_path = self._get_absolute_log_path(log)
            if os.path.basename(log).startswith("traceback"):
                mode = 0600
            else:
                mode = 0644
            save_to_file(log_path, self.cache[log], mode=mode)
            self.changed[log] = False


    @property
    def list(self):
        result = []

        if self.task.id is not None:
            task_dir = self.task.task_dir()
            if not task_dir.endswith("/"):
                task_dir += "/"

            # logs on disk
            for root, dirs, files in os.walk(task_dir):
                for i in files:
                    if i.endswith(".log.gz"):
                        i = i[:-3]
                    result.append(os.path.join(root, i)[len(task_dir):])

        # cached logs
        for log in self.cache:
            if log not in result:
                result.append(log)

        return result

    def _gzip_log(self, name):
        """gzip one log, do *not* throw any error on failure"""

        # compress only log files
        if not name.endswith(".log"):
            return

        import pipes
        path = self._get_absolute_log_path(name)
        if not os.path.isfile(path + ".gz"):
            run("gzip %s" % pipes.quote(path), can_fail=True, stdout=False)

    def gzip_logs(self):
        """gzip all task logs"""
        for i in self.list:
            self._gzip_log(i)


class Task(models.Model):
    """Model for hub_task table."""
    archive             = models.BooleanField(default=False, help_text=_("When a task is archived, it disappears from admin interface and cannot be accessed by taskd.<br />Make sure that archived tasks are finished and you won't need them anymore."))
    owner               = models.ForeignKey(User)
    worker              = models.ForeignKey(Worker, null=True, blank=True, help_text=_("A worker which has this task assigned."))
    parent              = models.ForeignKey("self", null=True, blank=True, help_text=_("Parent task."))
    state               = models.PositiveIntegerField(default=TASK_STATES["FREE"], choices=TASK_STATES.get_mapping(), help_text=_("Current task state."))
    label               = models.CharField(max_length=255, blank=True, help_text=_("Label, description or any reason for this task."))
    exclusive           = models.BooleanField(default=False, help_text=_("Exclusive tasks have highest priority. They are used e.g. when shutting down a worker."))

    method              = models.CharField(max_length=255, help_text=_("Method name represents appropriate task handler."))
    args                = kobo.django.fields.JSONField(blank=True, default={}, help_text=_("Method arguments. JSON serialized dictionary."))
    result              = models.TextField(blank=True, help_text=_("Task result. Do not store a lot of data here (use HubProxy.upload_task_log instead)."))
    comment             = models.TextField(null=True, blank=True)

    arch                = models.ForeignKey(Arch)
    channel             = models.ForeignKey(Channel)
    timeout             = models.PositiveIntegerField(null=True, blank=True, help_text=_("Task timeout. Leave blank for no timeout."))

    waiting             = models.BooleanField(default=False, help_text=_("Task is waiting until some subtasks finish."))
    awaited             = models.BooleanField(default=False, help_text=_("Task is awaited by another task."))

    dt_created          = models.DateTimeField(auto_now_add=True)
    dt_started          = models.DateTimeField(null=True, blank=True)
    dt_finished         = models.DateTimeField(null=True, blank=True)

    priority            = models.PositiveIntegerField(default=10, help_text=_("Priority."))
    weight              = models.PositiveIntegerField(default=1, help_text=_("Weight determines how many resources is used when processing the task."))

    resubmitted_by      = models.ForeignKey(User, null=True, blank=True, related_name="resubmitted_by1")
    resubmitted_from    = models.ForeignKey("self", null=True, blank=True, related_name="resubmitted_from1")

    subtask_count       = models.PositiveIntegerField(default=0, help_text=_("Subtask count.<br />This is a generated field."))

    # override default *objects* Manager
    objects = TaskManager()


    def __init__(self, *args, **kwargs):
        self.logs = TaskLogs(self)
        traceback = kwargs.pop("traceback", None)
        if traceback:
            self.logs["traceback.log"] = traceback

        stdout = kwargs.pop("stdout", None)
        if stdout:
            self.logs["stdout.log"] = stdout

        super(Task, self).__init__(*args, **kwargs)


    class Meta:
        ordering = ("-id", )


    def __unicode__(self):
        if self.parent:
            return u"#%s [method: %s, state: %s, worker: %s, parent: #%s]" % (self.id, self.method, self.get_state_display(), self.worker, self.parent.id)
        return u"#%s [method: %s, state: %s, worker: %s]" % (self.id, self.method, self.get_state_display(), self.worker)


    def save(self, *args, **kwargs):
        # save to db to precalculate subtask counts and obtain an ID (on insert) for stdout and traceback
        self.subtask_count = self.subtasks().count()
        super(self.__class__, self).save()
        self.logs.save()
        if self.parent:
            self.parent.save(*args, **kwargs)


    @classmethod
    def get_task_dir(cls, task_id, create=False):
        '''Task files (logs, etc.) are saved in TASK_DIR in following structure based on task_id:
        TASK_DIR/millions/tens_of_thousands/task_id/*
        '''
        task_id = int(task_id)
        third = task_id
        second = task_id // 10000 * 10000
        first = task_id // 1000000 * 1000000

        task_dir = os.path.abspath(settings.TASK_DIR)
        path = os.path.join(task_dir, str(first), str(second), str(third))
        path = os.path.abspath(path)
        if not path.startswith(task_dir):
            raise Exception('Possible hack, trying to read path "%s"' % path)

        if create and not os.path.isdir(path):
            os.makedirs(path, mode=0755)

        return path


    def task_dir(self, create=False):
        return Task.get_task_dir(self.id, create)


    @classmethod
    def create_task(cls, owner_name, label, method, args=None, comment=None, parent_id=None, worker_name=None, arch_name="noarch", channel_name="default", timeout=None, priority=10, weight=1, exclusive=False, resubmitted_by=None, resubmitted_from=None, state=None):
        """Create a new task."""
        task = cls()
        task.owner = User.objects.get(username=owner_name)
        task.label = label
        task.method = method
        task.args = args or {}
        task.comment = comment

        if parent_id is not None:
            task.parent = cls.objects.get(id=parent_id)

        if state is not None:
            task.state = state

        if worker_name is not None:
            task.worker = Worker.objects.get(name=worker_name)
            task.state = TASK_STATES["ASSIGNED"]

        task.resubmitted_by = resubmitted_by
        task.resubmitted_from = resubmitted_from

        task.arch = Arch.objects.get(name=arch_name)
        task.channel = Channel.objects.get(name=channel_name)
        task.priority = priority
        task.timeout = timeout
        task.weight = weight
        task.exclusive = exclusive

        # TODO: unsupported in Django 1.0
        #task.validate()
        task.save()
        return task.id


    @classmethod
    def create_shutdown_task(cls, owner_name, worker_name, kill=False):
        """Create a new ShutdownWorker task."""
        kwargs = {
            "owner_name": owner_name,
            "label": "Shutdown a worker.",
            "method": "ShutdownWorker",
            "args": {
                "kill": kill,
            },
            "worker_name": worker_name,
            "weight": 0,
            "exclusive": True,
        }
        return cls.create_task(**kwargs)


    def set_args(self, **kwargs):
        """Serialize args dictionary."""
        print >> sys.stderr, "DeprecationWarning: kobo.hub.models.Task.set_args() is deprecated. Use kobo.hub.models.Task.args instead."
        self.args = kwargs


    def get_args(self):
        """Deserialize args dictionary."""
        print >> sys.stderr, "DeprecationWarning: kobo.hub.models.Task.get_args() is deprecated. Use kobo.hub.models.Task.args instead."
        return self.args.copy()


    def get_args_display(self):
        """Deserialize args dictionary to human readable form"""
        from django.utils.datastructures import SortedDict
        result = SortedDict()
        for key, value in sorted(self.args.items()):
            result[key] = simplejson.dumps(value)
        return result


    def export(self, flat=True):
        """Export data for xml-rpc."""

        result = {
            "id": self.id,
            "owner": self.owner.username,
            "worker": self.worker_id,
            "parent": self.parent_id,
            "state": self.state,
            "label": self.label,

            "method": self.method,
            "args": self.args,
            "result": self.result,

            "exclusive": self.exclusive,
            "arch": self.arch_id,
            "channel": self.channel_id,
            "timeout": self.timeout,
            "waiting": self.waiting,
            "awaited": self.awaited,
            "dt_created": datetime.datetime.strftime(self.dt_created, "%F %R:%S"),
            "dt_started": self.dt_started and datetime.datetime.strftime(self.dt_started, "%Y-%m-%d %H:%M:%S") or None,
            "dt_finished": self.dt_finished and datetime.datetime.strftime(self.dt_finished, "%F %R:%S") or None,
            "priority": self.priority,
            "weight": self.weight,

            "resubmitted_by": getattr(self.resubmitted_by, "username", None),
            "resubmitted_from": getattr(self.resubmitted_from, "id", None),

            # used by task watcher
            "state_label": self.get_state_display(),
            "is_finished": self.is_finished(),
            "is_failed": self.is_failed(),
        }

        if not flat:
            result.update({
                "worker": self.worker and self.worker.export() or None,
                "parent": self.parent and self.parent.export() or None,
                "arch": self.arch.export(),
                "channel": self.channel.export(),
                "subtask_id_list": [ i.id for i in self.subtasks() ],
            })

        return result


    def subtasks(self):
        return Task.objects.filter(parent=self)


    @property
    def time(self):
        """return time spent in the task"""
        if not self.dt_started:
            return None
        elif not self.dt_finished:
            return datetime.datetime.now() - self.dt_started
        else:
            return self.dt_finished - self.dt_started


    def get_time_display(self):
        """display time in human readable form"""
        if self.time is None:
            return ""

        time = "%02d:%02d:%02d" % ((self.time.seconds/60/24), (self.time.seconds/60 % 24), (self.time.seconds % 60))
        if self.time.days:
            time = _("%s days, %s") % (self.time.days, time)
        return time
    get_time_display.short_description = "Time"


    def __lock(self, worker_id, new_state=TASK_STATES["ASSIGNED"], initial_states=None):
        """Critical section. Ensures that only one worker takes the task."""

        if type(initial_states) in (list, tuple):
            # filter out invalid state codes
            initial_states = [ i for i, j in TASK_STATES.get_mapping() if i in initial_states ]
            if not initial_states:
                # initial_states is empty
                initial_states = (TASK_STATES["FREE"], )
        else:
            initial_states = (TASK_STATES["FREE"], )

        # it is safe to pass initial_states directly to query,
        # because these values are checked in the code above
        query = """
UPDATE
  hub_task
SET
  state=%%s,
  worker_id=%%s,
  dt_started=%%s,
  dt_finished=%%s,
  waiting=%%s
WHERE
  id=%%s
  and state in (%(initial_states)s)
  and (worker_id is null or worker_id=%%s)
""" % { "initial_states": ",".join(( "'%s'" % i for i in initial_states )), }

        dt_started = self.dt_started
        if new_state == TASK_STATES["OPEN"]:
            dt_started = datetime.datetime.now()

        dt_finished = self.dt_finished
        if new_state in FINISHED_STATES:
            dt_finished = datetime.datetime.now()

        new_worker_id = worker_id
        if new_state == TASK_STATES["FREE"]:
            new_worker_id = None

        waiting = False

        transaction.enter_transaction_management()
        cursor = connection.cursor()
        cursor.execute(query, (new_state, new_worker_id, dt_started, dt_finished, waiting, self.id, worker_id))

        if cursor.rowcount == 0:
            transaction.rollback()
            transaction.leave_transaction_management()
            raise ObjectDoesNotExist()

        if cursor.rowcount > 1:
            transaction.rollback()
            transaction.leave_transaction_management()
            raise MultipleObjectsReturned()

        transaction.commit()
        transaction.leave_transaction_management()

        self.dt_started = dt_started
        self.dt_finished = dt_finished
        if new_worker_id is not None:
            self.worker = Worker.objects.get(id=new_worker_id)
        self.state = new_state
        self.waiting = waiting


    def free_task(self):
        """Free the task."""
        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["FREE"], initial_states=(TASK_STATES["FREE"], TASK_STATES["ASSIGNED"], TASK_STATES["CREATED"]))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot free task %d, state is %s" % (self.id, self.state))


    def assign_task(self, worker_id=None):
        """Assign the task to a worker identified by worker_id."""
        if worker_id is None:
            worker_id = self.worker_id

        try:
            self.__lock(worker_id, new_state=TASK_STATES["ASSIGNED"], initial_states=(TASK_STATES["FREE"], TASK_STATES["CREATED"]))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot assign task %d" % (self.id))


    def open_task(self, worker_id=None):
        """Open the task on a worker identified by worker_id."""
        if worker_id is None:
            worker_id = self.worker_id

        try:
            self.__lock(worker_id, new_state=TASK_STATES["OPEN"], initial_states=(TASK_STATES["FREE"], TASK_STATES["ASSIGNED"]))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot open task %d, state is %s" % (self.id, self.state))


    @transaction.commit_on_success
    def close_task(self, task_result=""):
        """Close the task and save result."""
        if task_result:
            self.result = task_result
            self.save()

        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["CLOSED"], initial_states=(TASK_STATES["OPEN"], ))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot close task %d, state is %s" % (self.id, self.state))
        self.logs.gzip_logs()


    @transaction.commit_on_success
    def cancel_task(self, user=None, recursive=True):
        """Cancel the task."""
        if user is not None and not user.is_superuser:
            if self.owner.username != user.username:
                raise Exception("You are not task owner or superuser.")

        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["CANCELED"], initial_states=(TASK_STATES["FREE"], TASK_STATES["ASSIGNED"], TASK_STATES["OPEN"], TASK_STATES["CREATED"]))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot cancel task %d, state is %s" % (self.id, self.state))

        if recursive:
            for task in self.subtasks():
                task.cancel_task(recursive=True)
        self.logs.gzip_logs()


    def cancel_subtasks(self):
        """Cancel all subtasks of the task."""
        result = True
        for task in self.subtasks():
            try:
                result &= task.cancel()
            except (MultipleObjectsReturned, ObjectDoesNotExist):
                result = False
        return result


    @transaction.commit_on_success
    def interrupt_task(self, recursive=True):
        """Set the task state to interrupted."""
        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["INTERRUPTED"], initial_states=(TASK_STATES["OPEN"], ))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot interrupt task %d, state is %s" % (self.id, self.state))

        if recursive:
            for task in self.subtasks():
                task.interrupt_task(recursive=True)
        self.logs.gzip_logs()


    @transaction.commit_on_success
    def timeout_task(self, recursive=True):
        """Set the task state to timeout."""
        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["TIMEOUT"], initial_states=(TASK_STATES["OPEN"], ))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot interrupt task %d, state is %s" % (self.id, self.state))

        if recursive:
            for task in self.subtasks():
                task.interrupt_task(recursive=True)
        self.logs.gzip_logs()


    @transaction.commit_on_success
    def fail_task(self, task_result=""):
        """Fail this task and save result."""
        if task_result:
            self.result = task_result
            self.save()

        try:
            self.__lock(self.worker_id, new_state=TASK_STATES["FAILED"], initial_states=(TASK_STATES["OPEN"], ))
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            raise Exception("Cannot fail task %i, state is %s" % (self.id, self.state))
        self.logs.gzip_logs()


    def is_finished(self):
        """Is the task finished? Task state can be one of: closed, interrupted, canceled, failed."""
        return self.state in FINISHED_STATES


    def is_failed(self):
        """Is the task successfuly finished? Task state must be closed."""
        return self.state in FAILED_STATES


    def resubmit_task(self, user):
        """Resubmit failed/canceled top-level task."""
        if not user.is_superuser:
            if self.owner.username != user.username:
                raise Exception("You are not task owner or superuser.")

        if self.parent:
            raise Exception("Task is not top-level: %s" % self.id)

        if self.exclusive:
            raise Exception("Cannot resubmit exclusive task: %s" % self.id)

        if self.state not in FAILED_STATES:
            states = [ TASK_STATES.get_value(i) for i in FAILED_STATES ]
            raise Exception("Task '%s' must be in: %s" % (self.id, states))

        kwargs = {
            "owner_name": self.owner.username,
            "label": self.label,
            "method": self.method,
            "args": self.args,
            "comment": self.comment,
            "parent_id": None,
            "worker_name": None,
            "arch_name": self.arch.name,
            "channel_name": self.channel.name,
            "priority": self.priority,
            "weight": self.weight,
            "exclusive": self.exclusive,
            "resubmitted_by": user,
            "resubmitted_from": self,
        }
        return Task.create_task(**kwargs)

    def clone_task(self, user, **kwargs):
        """Clone a task, override field values by kwargs."""
        if not user.is_superuser:
            raise Exception("You are not superuser.")

        if self.parent:
            raise Exception("Task is not top-level: %s" % self.id)

        kwargs.pop("resubmitted_by", None)
        kwargs.pop("resubmitted_from", None)

        new_kwargs = {
            "owner_name": self.owner.username,
            "label": self.label,
            "method": self.method,
            "args": self.args,
            "comment": self.comment,
            "parent_id": None,
            "worker_name": None,
            "arch_name": self.arch.name,
            "channel_name": self.channel.name,
            "priority": self.priority,
            "weight": self.weight,
            "exclusive": self.exclusive,
            "resubmitted_by": user,
            "resubmitted_from": self,
        }

        new_kwargs.update(kwargs)
        return Task.create_task(**new_kwargs)

    def wait(self, child_task_list=None):
        """Set this task as waiting and all subtasks in child_task_list as awaited.

        If child_task_list is None, process all related subtasks.
        """
        tasks = self.subtasks().filter(state__in=(TASK_STATES["FREE"], TASK_STATES["ASSIGNED"], TASK_STATES["OPEN"]))
        if child_task_list is not None:
            tasks = tasks.filter(id__in=child_task_list)

        for task in tasks:
            task.awaited = True
            task.save()

        self.waiting = True
        self.save()


    def check_wait(self, child_task_list=None):
        """Determine if all subtasks have finished."""
        tasks = self.subtasks()
        if child_task_list is not None:
            tasks = tasks.filter(id__in=child_task_list)

        finished = []
        unfinished = []
        for task in tasks:
            if task.is_finished():
                finished.append(task.id)
                task.awaited = False
                task.save()
            else:
                unfinished.append(task.id)

        return [finished, unfinished]
