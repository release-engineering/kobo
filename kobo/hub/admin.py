# -*- coding: utf-8 -*-


import django.contrib.admin as admin

from models import *


class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "label", "state", "owner", "dt_created", "dt_finished", "time", "arch", "channel")
    list_filter = ("method", "state")
    search_fields = ("id", "method", "label", "owner", "dt_created", "dt_finished")
    raw_id_fields = ('parent',)


admin.site.register(Arch)
admin.site.register(Channel)
admin.site.register(Worker)
admin.site.register(Task, TaskAdmin)
