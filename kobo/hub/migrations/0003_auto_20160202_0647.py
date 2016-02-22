# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hub', '0002_auto_20150722_0612'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='task',
            options={'ordering': ('-id',), 'permissions': (('can_see_traceback', 'Can see traceback'),)},
        ),
        migrations.AddField(
            model_name='worker',
            name='min_priority',
            field=models.PositiveIntegerField(default=0, help_text='Worker will take only tasks of this or higher priority.'),
        ),
    ]
