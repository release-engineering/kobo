# -*- coding: utf-8 -*-


import django.contrib.admin as admin

from models import *


class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "label", "state", "owner", "dt_created", "dt_finished", "time", "arch", "channel")
    list_filter = ("method", "state")
    search_fields = ("id", "method", "label", "owner__username", "dt_created", "dt_finished")
    raw_id_fields = ("parent", "owner", "resubmitted_by", "resubmitted_from")

class WorkerAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "ready", "max_load", "current_load", "task_count")

admin.site.register(Arch)
admin.site.register(Channel)
admin.site.register(Worker, WorkerAdmin)
admin.site.register(Task, TaskAdmin)
