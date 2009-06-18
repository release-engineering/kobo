# -*- coding: utf-8 -*-


import django.contrib.admin as admin

from models import *


class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "label", "state", "owner", "dt_created", "dt_finished", "arch", "channel")
    list_filter = ("method", "state", "owner")
    search_fields = ("id", "method", "label", "dt_created", "dt_finished")


admin.site.register(Arch)
admin.site.register(Channel)
admin.site.register(Worker)
admin.site.register(Task, TaskAdmin)
