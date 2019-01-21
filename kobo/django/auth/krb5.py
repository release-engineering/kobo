# -*- coding: utf-8 -*-


"""
# This is authentication backend for Django middleware.
# In settings.py you need to set:

MIDDLEWARE_CLASSES = (
    ...
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    ...
)
AUTHENTICATION_BACKENDS = (
    'kobo.django.auth.krb5.RemoteUserBackend',
)


# Add login and logout adresses to urls.py:

urlpatterns = [
    ...
    url(r'^auth/krb5login/$',
    django.views.generic.TemplateView.as_view(template = 'auth/krb5login.html'),
    url(r'^auth/logout/$', 'django.contrib.auth.views.logout', kwargs={"next_page": "/"}),
    ...
]


# Set a httpd config to protect krb5login page with kerberos.
# You need to have mod_auth_kerb installed to use kerberos auth.
# Httpd config /etc/httpd/conf.d/<project>.conf should look like this:

<Location "/">
    SetHandler python-program
    PythonHandler django.core.handlers.modpython
    SetEnv DJANGO_SETTINGS_MODULE <project>.settings
    PythonDebug On
</Location>

<Location "/auth/krb5login">
    AuthType Kerberos
    AuthName "<project> Kerberos Authentication"
    KrbMethodNegotiate on
    KrbMethodK5Passwd off
    KrbServiceName HTTP
    KrbAuthRealms EXAMPLE.COM
    Krb5Keytab /etc/httpd/conf/http.<hostname>.keytab
    KrbSaveCredentials off
    Require valid-user
</Location>
"""


from django.contrib.auth.backends import RemoteUserBackend

class Krb5RemoteUserBackend(RemoteUserBackend):
    def clean_username(self, username):
        # remove @REALM from username
        return username.split("@")[0]
