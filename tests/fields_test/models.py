# -*- coding: utf-8 -*-

from kobo.django.fields import JSONField

from django.db import models


class DummyModel(models.Model):
    field = JSONField()


class DummyDefaultModel(models.Model):
    field = JSONField(default={})

class DummyNotHumanModel(models.Model):
    field = JSONField(default={}, human_readable = True)
