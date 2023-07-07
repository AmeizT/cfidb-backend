from apps.bookkeeper.views import (
    AssetView, 
    ExpenditureView,
    IncomeView,
    PayrollView 
)
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'assets', AssetView, basename='assets')
router.register(r'expenditure', ExpenditureView, basename='expenditure')
router.register(r'income', IncomeView, basename='income')
router.register(r'payroll', PayrollView, basename='payroll')

urlpatterns = [
    path('', include(router.urls)),
]



