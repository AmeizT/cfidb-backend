from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.chat.views import MessageView, MessengerView, MessageAdminView

router = DefaultRouter()

router.register(r"messages", MessageView, basename="messages")
router.register(r"messenger", MessengerView, basename="messenger")

# ADMIN URLS

router.register(r"messages-tracker", MessageAdminView, basename="messages-admin")

urlpatterns = [
    path("", include(router.urls)),
]
