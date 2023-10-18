from apps.strategy.views import (
    StrategyView,
    StrategyLegacyView, 
    StrategyLegacyTrackerView,
)
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'strategy', StrategyView, basename='strategy')
router.register(r'strategy-legacy', StrategyLegacyView, basename='strategy_legacy')
router.register(r'strategy-tracker', StrategyLegacyTrackerView, basename='strategy_tracker')

urlpatterns = [
    path('', include(router.urls)),
]



