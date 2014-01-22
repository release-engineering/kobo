# -*- coding: utf-8 -*-

DATABASES = {
    'default': {
        'NAME': ':memory:',
        'ENGINE': 'django.db.backends.sqlite3'
    }
}

INSTALLED_APPS = (
    'fields_test',
)

SECRET_KEY = 'whatever'
