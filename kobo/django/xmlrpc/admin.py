# -*- coding: utf-8 -*-


from __future__ import absolute_import
import django.contrib.admin as admin

from .models import XmlRpcLog


admin.site.register(XmlRpcLog)
