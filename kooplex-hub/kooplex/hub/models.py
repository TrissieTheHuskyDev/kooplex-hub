﻿from django.db import models

class Notebook(models.Model):
    id = models.UUIDField(primary_key=True)
    username = models.CharField(max_length=200)
    host = models.CharField(max_length=200)
    ip = models.CharField(max_length=32)
    port = models.IntegerField()
    image = models.CharField(max_length=200)
    container = models.CharField(max_length=200)
    path = models.CharField(max_length=200)
    command = models.TextField()
    url = models.CharField(max_length=200)

