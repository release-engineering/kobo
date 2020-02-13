# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hub', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='task',
            name='parent',
            field=models.ForeignKey(blank=True, to='hub.Task', help_text='Parent task.',
                on_delete=models.CASCADE, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='resubmitted_by',
            field=models.ForeignKey(related_name='resubmitted_by1', blank=True,
                to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='resubmitted_from',
            field=models.ForeignKey(related_name='resubmitted_from1',
                blank=True, to='hub.Task', on_delete=models.CASCADE, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='worker',
            field=models.ForeignKey(blank=True, to='hub.Worker',
                help_text='A worker which has this task assigned.',
                on_delete=models.CASCADE, null=True),
        ),
    ]
