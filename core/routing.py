
from django.urls import re_path
from core.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<doctor_id>\d+)/(?P<patient_id>\d+)/$', ChatConsumer.as_asgi()),
]
