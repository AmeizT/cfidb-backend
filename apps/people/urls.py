from apps.people.views import (
    AttendanceView,
    HCAttendanceView,
    HomeCellView,
    KinView,
    MemberView,
    CreateMemberView,
    AttendanceAdminView,
    MemberAdminView,
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'attendance', AttendanceView, basename='attendance')
router.register(r'homecell', HomeCellView, basename='homecell')
router.register(r'homecell-attendance', HCAttendanceView, basename='homecell_attendance')
router.register(r'kin', KinView, basename='kin')
router.register(r'members', MemberView, basename='members')
router.register(r'member/add', CreateMemberView, basename='members_add')
router.register(r'attendance-tracker', AttendanceAdminView, basename='admin_attendance')
router.register(r'members-tracker', MemberAdminView, basename='admin_members')


urlpatterns = [
    path('', include(router.urls)),
]
