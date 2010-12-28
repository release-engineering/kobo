# -*- coding: utf-8 -*-


import os

os.environ['DJANGO_SETTINGS_MODULE'] = '{{ project_name }}.settings'
import django.core.handlers.wsgi


application = django.core.handlers.wsgi.WSGIHandler()
