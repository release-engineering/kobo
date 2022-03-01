from django.contrib.auth.admin import *
import django.contrib.admin as admin
from kobo.django.django_version import django_version_ge

from kobo.django.auth.models import *

# users are not displayed on admin page since migrations were introduced
if django_version_ge("1.9.0"):
    admin.site.register(User, UserAdmin)