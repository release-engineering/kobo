# Generated by Django 3.2.20 on 2023-08-22 09:45

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileupload',
            name='size',
            field=models.BigIntegerField(validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
