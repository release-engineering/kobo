# Generated by Django 2.2.24 on 2022-02-02 16:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUpload',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('checksum', models.CharField(max_length=255)),
                ('size', models.PositiveIntegerField()),
                ('target_dir', models.CharField(max_length=255)),
                ('upload_key', models.CharField(max_length=255)),
                ('state', models.PositiveIntegerField(choices=[(0, 'NEW'), (1, 'STARTED'), (2, 'FINISHED'), (3, 'FAILED')], default=0)),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_finished', models.DateTimeField(blank=True, null=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-dt_created', 'name'),
            },
        ),
    ]
