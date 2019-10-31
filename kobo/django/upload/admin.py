# -*- coding: utf-8 -*-


import django.contrib.admin as admin

from .models import FileUpload


class FileUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'name', 'size', 'upload_key', 'state', 'dt_created', 'dt_finished')
    list_filter = ('owner', 'state')
    search_fields = ('id', 'upload_key', 'name', 'dt_created', 'dt_finished')

admin.site.register(FileUpload, FileUploadAdmin)
