from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/parking/$', consumers.ParkingConsumer.as_asgi()),
    re_path(r'ws/nearest/$', consumers.NearestParkingConsumer.as_asgi()),
]