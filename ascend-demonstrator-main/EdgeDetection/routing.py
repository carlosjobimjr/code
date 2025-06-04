from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/edge_detection/$', consumers.EdgeDetectionConsumer.as_asgi()),
]