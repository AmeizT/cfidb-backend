from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.office.views import ( CircularView, CreateMinutesView, MeetingView, MinutesView )

router = DefaultRouter()

router.register(r'meetings', MeetingView, basename='meetings')
router.register(r'minutes', MinutesView, basename='minutes')
router.register(r'circular', CircularView, basename='circular')
router.register(r'create-minutes', CreateMinutesView, basename='create_minutes')

urlpatterns = [
    path('', include(router.urls)),
]