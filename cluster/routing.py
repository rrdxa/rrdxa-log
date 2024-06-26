from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/notify/$", consumers.PGConsumer.as_asgi()),
    re_path(r"ws/spot/$", consumers.SpotConsumer.as_asgi()),
]
