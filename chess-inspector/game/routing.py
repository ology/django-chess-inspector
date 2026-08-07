from django.urls import re_path

from . import consumers

websocket_url_patterns = [
    re_path(r'ws/socket-server/(?P<game_id>\d+)/$', consumers.ChatConsumer.as_asgi())
]
