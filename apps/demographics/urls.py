from apps.demographics.views import (
    AttendanceView, 
    MemberView,
    CombineAttendanceView, 
    CombineMemberView
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'church/attendance', AttendanceView, basename='attendance')
router.register(r'churc/members', MemberView, basename='members')
router.register(r'admin/attendance', CombineAttendanceView, basename='combine_attendance')
router.register(r'admin/members', CombineAttendanceView, basename='combine_members')


urlpatterns = [
    path('', include(router.urls)),
]



