from django.db import models
from django.utils import timezone

class Profile(models.Model):
    account_id = models.BigIntegerField(blank=False)
    last_play = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)

class Game(models.Model):
    account_id = models.BigIntegerField(blank=False)
    fen = models.CharField(max_length=100, blank=True)
