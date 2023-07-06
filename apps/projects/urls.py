from apps.projects.views import (ProjectView)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'projects', ProjectView, basename='projects')

urlpatterns = [
    path('', include(router.urls)),
]



