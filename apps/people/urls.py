from apps.people.views import (
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
]
