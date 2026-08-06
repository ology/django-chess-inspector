from django.db import models
from django.utils import timezone

class Profile(models.Model):
    account_id = models.BigIntegerField(blank=False)
    last_play = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(default=timezone.now)

class Game(models.Model):
    account_id = models.BigIntegerField(blank=False)
    fen = models.CharField(max_length=100, blank=True)
    last_fen = models.CharField(max_length=100, blank=True)
    pgn_filename = models.CharField(max_length=255, blank=True, default='')
    pgn_date = models.CharField(max_length=50, blank=True, default='')
    pgn_site = models.CharField(max_length=200, blank=True, default='')
    pgn_white = models.CharField(max_length=200, blank=True, default='')
    pgn_black = models.CharField(max_length=200, blank=True, default='')
    # List of FEN strings for the currently-loaded PGN's mainline, one per
    # ply (including the starting position at index 0). Empty when no PGN
    # is loaded. This drives the play forward/backward/end controls -
    # previously that list only ever lived in a cookie on the client, which
    # worked but required fragile manual escaping. Storing it here means
    # any worker process can render it, not just whichever one handled the
    # upload.
    fens = models.JSONField(default=list, blank=True)
    updated = models.DateTimeField(auto_now=True)
    