from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from parking_app import consumers

websocket_urlpatterns = [
    re_path(r'ws/parking/$', consumers.ParkingConsumer.as_asgi()),
    re_path(r'ws/nearest/$', consumers.NearestParkingConsumer.as_asgi()),
]