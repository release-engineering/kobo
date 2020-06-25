from __future__ import absolute_import
import django.contrib.admin as admin
from .models import SimpleState


class SimpleStateAdmin(admin.ModelAdmin):
    list_display = ('__str__', '__unicode__', 'id', 'comment')

admin.site.register(SimpleState, SimpleStateAdmin)
