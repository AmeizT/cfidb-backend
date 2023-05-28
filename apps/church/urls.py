from apps.church.views import (
    AttendanceView,
    ChurchView, 
    MemberView,
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r"attendance", AttendanceView, basename="attendance")
router.register(r"churches", ChurchView, basename="church")
router.register(r"members", MemberView, basename="members")

urlpatterns = [
    path("", include(router.urls)),
]



