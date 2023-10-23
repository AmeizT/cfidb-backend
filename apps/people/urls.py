from apps.people.views import (
    AttendanceView,
    AttendanceRegisterView,
    HCAttendanceView,
    HomeCellView,
    KindredView,
    CreateKindredView,
    MemberView,
    CreateMemberView,
    AttendanceAdminView,
    MemberAdminView,
    TallyView,
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'attendance', AttendanceView, basename='attendance')
router.register(r'attendance-register', AttendanceRegisterView, basename='attendance_register')
router.register(r'homecell', HomeCellView, basename='homecell')
router.register(r'homecell-attendance', HCAttendanceView, basename='homecell_attendance')
router.register(r'kindred', KindredView, basename='kindred')
router.register(r'create-kindred', CreateKindredView, basename='create_kindred')
router.register(r'members', MemberView, basename='members')
router.register(r'create-member', CreateMemberView, basename='create_members')
router.register(r'attendance-tracker', AttendanceAdminView, basename='admin_attendance')
router.register(r'members-tracker', MemberAdminView, basename='admin_members')
router.register(r'tally', TallyView, basename='tally')


urlpatterns = [
    path('', include(router.urls)),
]
