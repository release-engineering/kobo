# -*- coding: utf-8 -*-


from django.db import models
from django.conf import settings
import six


@six.python_2_unicode_compatible
class XmlRpcLog(models.Model):
    dt_inserted = models.DateTimeField(auto_now_add=True)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    method      = models.CharField(max_length=255)
    args        = models.TextField(blank=True)

    def __str__(self):
        return u"%s: %s" % (self.user, self.method)
