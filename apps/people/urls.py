from apps.people.views import (
    AttendanceView,
    HCAttendanceView, 
    HomeCellView,
    MemberView,
    CreateMemberView,
    CombineAttendanceView, 
    CombineMemberView
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'attendance', AttendanceView, basename='attendance')
router.register(r'homecell', HomeCellView, basename='homecell')
router.register(r'hcattendance', HCAttendanceView, basename='hcattendance')
router.register(r'members', MemberView, basename='members')
router.register(r'member/add', CreateMemberView, basename='members_add')
router.register(r'admin/attendance', CombineAttendanceView, basename='admin_attendance')
router.register(r'admin/members', CombineAttendanceView, basename='admin_members')


urlpatterns = [
    path('', include(router.urls)),
]



