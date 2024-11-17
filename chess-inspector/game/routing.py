from django.urls import path, re_path

from . import consumers

websocket_url_patterns = [
    re_path(r'ws/socket-server/', consumers.ChatConsumer.as_asgi())
]
