from django.contrib.auth.admin import *
import django.contrib.admin as admin

from kobo.django.auth.models import *

# users are not displayed on admin page since migrations were introduced
admin.site.register(User, UserAdmin)
