from apps.finance.views import (
    AssetView, 
    ExpenditureView,
    IncomeView 
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'church/assets', AssetView, basename='assets')
router.register(r'expenditure', ExpenditureView, basename='expenditure')
router.register(r'income', IncomeView, basename='income')

urlpatterns = [
    path('', include(router.urls)),
]



