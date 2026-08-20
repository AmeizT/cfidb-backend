from apps.resources.views import (ResourceView)
from django.urls import path, include, re_path
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register(r'resources', ResourceView, basename='resources')

urlpatterns = [
    path('', include(router.urls)),
]



