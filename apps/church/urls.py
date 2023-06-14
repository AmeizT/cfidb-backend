from apps.church.views import ChurchView
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r"churches", ChurchView, basename="church")

urlpatterns = [
    path("", include(router.urls)),
]



