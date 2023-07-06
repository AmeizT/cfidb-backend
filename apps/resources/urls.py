from apps.resources.views import (ResourceView)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'resources', ResourceView, basename='resources')

urlpatterns = [
    path('', include(router.urls)),
]



