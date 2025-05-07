from apps.people.views.belong import check_member_existence, get_member_data, reset_member_pin, set_member_pin, verify_member_pin
from apps.people.views.views import (
    AttendanceView,
    CreateHomecellView,
    CreateTallyView,
    HomecellView,
    JuniorMemberView,
    MemberView,
    TallyView,
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'attendance', AttendanceView, basename='attendance')
router.register(r'homecells', HomecellView, basename='homecell')
router.register(r'junior_members', JuniorMemberView, basename='junior_members')
router.register(r'members', MemberView, basename='members')
router.register(r'tally', TallyView, basename='tally')


urlpatterns = [
    path('', include(router.urls)),
    path('belong/check-member/', check_member_existence, name='check-member'),
    path('belong/check-in/', verify_member_pin, name='verify-member-pin'),
    path('belong/set-pin/', set_member_pin, name='set-member-pin'),
    path('belong/reset-pin/', reset_member_pin, name='reset-member-pin'),
    path('belong/member/<str:member_id>/', get_member_data, name='get_member_data'),
]
