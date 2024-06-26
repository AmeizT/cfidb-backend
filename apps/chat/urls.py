from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.chat.views import MessageView, MessengerView

router = DefaultRouter()

router.register(r"messages", MessageView, basename="messages")
router.register(r"messenger", MessengerView, basename="messenger")

urlpatterns = [
    path("", include(router.urls)),
]
