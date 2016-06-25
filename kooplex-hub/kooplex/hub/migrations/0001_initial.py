# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-24 23:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Notebook',
            fields=[
                ('id', models.UUIDField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=200)),
                ('host', models.CharField(max_length=200)),
                ('ip', models.CharField(max_length=32)),
                ('port', models.IntegerField()),
                ('image', models.CharField(max_length=200)),
                ('container', models.CharField(max_length=200)),
                ('path', models.CharField(max_length=200)),
                ('command', models.TextField()),
                ('url', models.CharField(max_length=200)),
            ],
        ),
    ]
