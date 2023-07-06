from django.urls import path, include
from apps.events.views import (EventView)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'events', EventView, basename='events')

urlpatterns = [
    path('', include(router.urls)),
]



