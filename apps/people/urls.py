from apps.people.views.belong import (
    check_member_existence, 
    get_member_data, 
    reset_member_pin, 
    set_member_pin, 
    verify_member_pin
)
from apps.people.views import (
    AssemblyMembershipViewSet,
    AttendanceViewSet,
    HomecellView,
    HouseholdMemberViewSet,
    HouseholdViewSet,
    JuniorMemberView,
    MemberView,
    MemberTransferRequestViewSet,
    FormerMemberViewSet,
    SundaySchoolAttendanceViewSet,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = "people"

router = DefaultRouter()

router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'sunday-school-attendance', SundaySchoolAttendanceViewSet, basename='sunday-school-attendance')
router.register(r'homecells', HomecellView, basename='homecell')
router.register(r'junior_members', JuniorMemberView, basename='junior_members')
router.register(r'members', MemberView, basename='members')
router.register(r'member-transfers', MemberTransferRequestViewSet, basename='member-transfers')
router.register(r'assembly-memberships', AssemblyMembershipViewSet, basename='assembly-memberships')
router.register(r'former-members', FormerMemberViewSet, basename='former-members')
router.register(r'households', HouseholdViewSet, basename='households')
router.register(r'household-members', HouseholdMemberViewSet, basename='household-members')

urlpatterns = [
    path('', include(router.urls)),
    path('belong/check-member/', check_member_existence, name='check-member'),
    path('belong/check-in/', verify_member_pin, name='verify-member-pin'),
    path('belong/set-pin/', set_member_pin, name='set-member-pin'),
    path('belong/reset-pin/', reset_member_pin, name='reset-member-pin'),
    path('belong/member/<str:member_key>/', get_member_data, name='get_member_data'),
]
