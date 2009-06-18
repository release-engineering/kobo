# -*- coding: utf-8 -*-


import django.contrib.admin as admin
from django.db import models
from django.contrib.auth.models import User


class XmlRpcLog(models.Model):
    dt_inserted = models.DateTimeField(auto_now_add=True)
    user        = models.ForeignKey(User, null=True, blank=True)
    method      = models.CharField(max_length=255)
    args        = models.TextField(blank=True)

    def __unicode__(self):
        return u"%s: %s" % (self.user, self.method)
