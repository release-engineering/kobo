# Settings for Django testcases against kobo hub
import os
import kobo
import tempfile
from django import VERSION

KOBO_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'kobo')
)

SECRET_KEY = "key"
XMLRPC_METHODS = []
# When the following objects are destroyed
# the temporary directories are deleted.
TASK_DIR_OBJ = tempfile.TemporaryDirectory(prefix="kobo-test-tasks-")
UPLOAD_DIR_OBJ = tempfile.TemporaryDirectory(prefix="kobo-test-dir-")
WORKER_DIR_OBJ = tempfile.TemporaryDirectory(prefix="kobo-worker-")

TASK_DIR = TASK_DIR_OBJ.name
UPLOAD_DIR = UPLOAD_DIR_OBJ.name
WORKER_DIR = WORKER_DIR_OBJ.name

# The middleware and apps below are the bare minimum required
# to let kobo.hub load successfully

if VERSION[0:3] < (1, 10, 0):
    MIDDLEWARE_CLASSES = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'kobo.django.auth.middleware.LimitedRemoteUserMiddleware',
        'kobo.hub.middleware.WorkerMiddleware',
    )
if VERSION[0:3] >= (1, 10, 0):
    MIDDLEWARE = (
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'kobo.django.auth.middleware.LimitedRemoteUserMiddleware',
        'kobo.hub.middleware.WorkerMiddleware',
    )


INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'kobo.django',
    'kobo.hub',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'testdatabase',
    }
}

# We need to specify the template dirs because:
# - the admin/templates don't belong to a particular django app, instead
#   they're intended to be copied to another app by a custom command, but
#   we don't want to run that during the tests
# - automatic lookup of templates under kobo/hub isn't working for some reason,
#   not sure why, but might be related to use of deprecated arguments in
#   render_to_string (FIXME)
#
# The way to specify the template dirs differs between newer and older versions of Django
if VERSION[0:3] < (1, 9, 0):
    TEMPLATE_DIRS = (
        os.path.join(KOBO_DIR, 'admin/templates/hub/templates'),
        os.path.join(KOBO_DIR, 'hub/templates'),
    )
if VERSION[0:3] >= (1, 9, 0):
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': (
                os.path.join(KOBO_DIR, 'admin/templates/hub/templates'),
                os.path.join(KOBO_DIR, 'hub/templates')
            ),
            'APP_DIRS': True
        }
    ]

ROOT_URLCONF = 'tests.hub_urls'

STATIC_URL = os.path.join(os.path.dirname(kobo.__file__), "hub", "static") + '/'
