import django.contrib.admin as admin
from models import *


class SimpleStateAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'id', 'comment')

admin.site.register(SimpleState, SimpleStateAdmin)
