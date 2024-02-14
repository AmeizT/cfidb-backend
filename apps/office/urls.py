from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.office.views import ( 
    CircularView, 
    MeetingView, 
    MinutesView, 
    StrategyView, 
)

router = DefaultRouter()

router.register(r'meetings', MeetingView, basename='meetings')
router.register(r'strategies', MeetingView, basename='strategies')
router.register(r'minutes', MinutesView, basename='minutes')
router.register(r'documents', CircularView, basename='circulars')
router.register(r'church-strategy', StrategyView, basename='church_strategy')

urlpatterns = [
    path('', include(router.urls)),
]
