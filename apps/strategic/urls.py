from apps.strategic.views import (
    StrategyView,
    StrategyLegacyView, 
)
from django.urls import path, include
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register(r'strategy', StrategyView, basename='strategy')
router.register(r'strategy-legacy', StrategyLegacyView, basename='strategy_legacy')

urlpatterns = [
    path('', include(router.urls)),
]



