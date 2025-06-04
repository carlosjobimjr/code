import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter, get_default_application
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WP1_4.settings')
django_asgi_app = get_asgi_application()

from Main.routing import websocket_urlpatterns as main_ws_urlpatterns
from EnergyCapture.routing import websocket_urlpatterns as energy_capture_ws_urlpatterns
from EdgeDetection.routing import websocket_urlpatterns as edge_detection_ws_urlpatterns


# Combine all WebSocket URL patterns
ws_urlpatterns = (
    main_ws_urlpatterns + 
    energy_capture_ws_urlpatterns + 
    edge_detection_ws_urlpatterns  # Add this line
)


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(ws_urlpatterns))
    ),
})