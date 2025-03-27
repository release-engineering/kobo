# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0004_alter_task_worker'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='canceled_by',
            field=models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE),
        ),
    ]
