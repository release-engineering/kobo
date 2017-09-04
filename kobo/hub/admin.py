# -*- coding: utf-8 -*-


from __future__ import absolute_import
import django.contrib.admin as admin

from .models import Arch, Channel, Task, Worker


class ArchAdmin(admin.ModelAdmin):
    list_display = ("name", "pretty_name")
    search_fields = ("name", "pretty_name")

class ChannelAdmin(admin.ModelAdmin):
    search_fields = ("name",)

class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "label", "state", "owner", "dt_created", "dt_finished", "time", "arch", "channel")
    list_filter = ("method", "state", "priority", "arch")
    search_fields = ("id", "method", "label", "owner__username", "dt_created", "dt_finished")
    raw_id_fields = ("parent", "owner", "resubmitted_by", "resubmitted_from")

class WorkerAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "ready", "max_load", "current_load", "task_count","min_priority")
    list_filter = ("enabled", "ready")
    search_fields = ("name",)

admin.site.register(Arch, ArchAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Worker, WorkerAdmin)
