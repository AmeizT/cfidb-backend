from django.urls import path, include
from apps.strategy.views import StrategyView, StrategyTrackerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'strategy', StrategyView, basename='strategy')
router.register(r'strategy-tracker', StrategyTrackerView, basename='strategy_tracker')

urlpatterns = [
    path('', include(router.urls)),
]



