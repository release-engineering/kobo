from kobo.django.django_version import django_version_ge

if django_version_ge('3.2.0'):
    pass
else:
    default_app_config = 'kobo.django.auth.apps.AuthConfig'
