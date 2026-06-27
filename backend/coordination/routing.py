from django.urls import path

from .consumers import SituationConsumer

websocket_urlpatterns = [
    path(
        "ws/situations/<uuid:situation_id>/",
        SituationConsumer.as_asgi(),
    ),
]

