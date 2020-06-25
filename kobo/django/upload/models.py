# -*- coding: utf-8 -*-


import os

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

from kobo.shortcuts import random_string
from kobo.types import Enum
import six


UPLOAD_STATES = Enum(
    "NEW",
    "STARTED",
    "FINISHED",
    "FAILED",
)


@six.python_2_unicode_compatible
class FileUpload(models.Model):
    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name        = models.CharField(max_length=255)
    checksum    = models.CharField(max_length=255)
    size        = models.PositiveIntegerField()
    target_dir = models.CharField(max_length=255)
    upload_key  = models.CharField(max_length=255)
    state       = models.PositiveIntegerField(default=0, choices=UPLOAD_STATES.get_mapping())
    dt_created  = models.DateTimeField(auto_now_add=True)
    dt_finished = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-dt_created", "name", )
#        unique_together = (
#            ("name", "target_dir")
#        )

    def export(self):
        result = {
            "owner": self.owner_id,
            "name": self.name,
            "checksum": self.checksum,
            "size": self.size,
            "target_dir": self.target_dir,
            "state": self.state,
        }
        return result

    def get_full_path(self):
        return os.path.abspath(os.path.join(self.target_dir, self.name))

    def __str__(self):
        return six.text_type(os.path.join(self.target_dir, self.name))

    def save(self, *args, **kwargs):
        if not self.upload_key:
            self.upload_key = random_string(64)
        if self.state == UPLOAD_STATES['FINISHED']:
            if FileUpload.objects.filter(state = UPLOAD_STATES['FINISHED'], name = self.name).exclude(id = self.id).count() != 0:
                # someone created same upload faster
                self.state == UPLOAD_STATES['FAILED']
        super(FileUpload, self).save(*args, **kwargs)

    def delete(self):
        super(FileUpload, self).delete()
        # if file was successfully uploaded it should be removed from
        # filesystem, otherwise it shouldn't be there
        if self.state == UPLOAD_STATES['FINISHED']:
            try:
                os.unlink(self.get_full_path())
            except OSError as ex:
                if ex.errno != 2:
                    raise

            upload_dir = getattr(settings, "UPLOAD_DIR", None)
            if upload_dir is not None:
                upload_dir = os.path.abspath(upload_dir)
                file_dir = os.path.dirname(self.get_full_path())
                while 1:
                    if not file_dir.startswith(upload_dir):
                        break
                    if file_dir == upload_dir:
                        break
                    try:
                        os.rmdir(file_dir)
                    except OSError as ex:
                        break
                    file_dir = os.path.split(file_dir)[0]
