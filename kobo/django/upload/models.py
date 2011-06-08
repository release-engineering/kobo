# -*- coding: utf-8 -*-


import os

from django.db import models
from django.contrib.auth.models import User

from kobo.shortcuts import random_string
from kobo.types import Enum


UPLOAD_STATES = Enum(
    "NEW",
    "STARTED",
    "FINISHED",
    "FAILED",
)


class FileUpload(models.Model):
    owner       = models.ForeignKey(User)
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
        return os.path.join(self.target_dir, self.name)

    def __unicode__(self):
        return unicode(os.path.join(self.target_dir, self.name))

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
            except OSError, ex:
                if ex.errno != 2:
                    raise
