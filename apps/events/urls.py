from apps.events.views import (
    EventView 
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'events', EventView, basename='messages')

urlpatterns = [
    path('', include(router.urls)),
]



