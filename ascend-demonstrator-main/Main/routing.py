from django.urls import path, re_path
from .consumers import SubProcessConsumer, OPCUAConsumer, SensorConsumer, ShellyDataConsumer
websocket_urlpatterns = [
    re_path(r"ws/Main/SubProcess/(?P<room_name>\w+)/$", SubProcessConsumer.as_asgi()),
    re_path(r'ws/Main/OPCUA/(?P<room_name>\w+)/$', OPCUAConsumer.as_asgi()),
    re_path(r'ws/Main/sensors/(?P<id>\d+)/$', SensorConsumer.as_asgi()),
    re_path(r'ws/Main/shelly/$', ShellyDataConsumer.as_asgi()), 
]