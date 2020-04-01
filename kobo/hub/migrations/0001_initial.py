# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import kobo.django.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Arch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='i386, ia64, ...', unique=True, max_length=16)),
                ('pretty_name', models.CharField(help_text='i386, Itanium, ...', unique=True, max_length=64)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name_plural': 'arches',
            },
        ),
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Channel name', max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('archive', models.BooleanField(default=False, help_text="When a task is archived, it disappears from admin interface and cannot be accessed by taskd.<br />Make sure that archived tasks are finished and you won't need them anymore.")),
                ('state', models.PositiveIntegerField(default=0, help_text='Current task state.', choices=[(0, 'FREE'), (1, 'ASSIGNED'), (2, 'OPEN'), (3, 'CLOSED'), (4, 'CANCELED'), (5, 'FAILED'), (6, 'INTERRUPTED'), (7, 'TIMEOUT'), (8, 'CREATED')])),
                ('label', models.CharField(help_text='Label, description or any reason for this task.', max_length=255, blank=True)),
                ('exclusive', models.BooleanField(default=False, help_text='Exclusive tasks have highest priority. They are used e.g. when shutting down a worker.')),
                ('method', models.CharField(help_text='Method name represents appropriate task handler.', max_length=255)),
                ('args', kobo.django.fields.JSONField(default={}, help_text='Method arguments. JSON serialized dictionary.', blank=True)),
                ('result', models.TextField(help_text='Task result. Do not store a lot of data here (use HubProxy.upload_task_log instead).', blank=True)),
                ('comment', models.TextField(null=True, blank=True)),
                ('timeout', models.PositiveIntegerField(help_text='Task timeout. Leave blank for no timeout.', null=True, blank=True)),
                ('waiting', models.BooleanField(default=False, help_text='Task is waiting until some subtasks finish.')),
                ('awaited', models.BooleanField(default=False, help_text='Task is awaited by another task.')),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_started', models.DateTimeField(null=True, blank=True)),
                ('dt_finished', models.DateTimeField(null=True, blank=True)),
                ('priority', models.PositiveIntegerField(default=10, help_text='Priority.')),
                ('weight', models.PositiveIntegerField(default=1, help_text='Weight determines how many resources is used when processing the task.')),
                ('subtask_count', models.PositiveIntegerField(default=0, help_text='Subtask count.<br />This is a generated field.')),
                ('arch', models.ForeignKey(to='hub.Arch', on_delete=models.CASCADE)),
                ('channel', models.ForeignKey(to='hub.Channel', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
        migrations.CreateModel(
            name='Worker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('worker_key', models.CharField(help_text='Worker authentication key.<br />Leave blank to generate new key.', unique=True, max_length=255, blank=True)),
                ('name', models.CharField(help_text='Worker hostname.', unique=True, max_length=128)),
                ('enabled', models.BooleanField(default=True, help_text='Enabled workers are allowed to process tasks.')),
                ('max_load', models.PositiveIntegerField(default=1, help_text='Maximum allowed load (sum of task weights).', blank=True)),
                ('max_tasks', models.PositiveIntegerField(default=0, help_text='Maximum assigned tasks. (0 = no limit)', blank=True)),
                ('ready', models.BooleanField(default=True, help_text='Is the worker ready to take new tasks?<br />This is a generated field.')),
                ('task_count', models.PositiveIntegerField(default=0, help_text='Count of processed tasks.<br />This is a generated field.', blank=True)),
                ('current_load', models.PositiveIntegerField(default=0, help_text='Sum of task weights.<br />This is a generated field.', blank=True)),
                ('arches', models.ManyToManyField(help_text='Supported architectures', to='hub.Arch')),
                ('channels', models.ManyToManyField(to='hub.Channel')),
            ],
        ),
    ]
