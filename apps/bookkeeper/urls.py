from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.bookkeeper.views import (
    AssetAdminView,
    AssetView,
    CreateTitheView,
    ExpenditureAdminView,
    ExpenditureView,
    FixedExpenditureView,
    IncomeAdminView,
    IncomeView,
    PayrollView,
    PledgeView,
    TitheView,
)

router = DefaultRouter()

router.register(r'assets', AssetView, basename='assets')
router.register(r'create-tithe', CreateTitheView, basename='create_tithe')
router.register(r'expenditure', ExpenditureView, basename='expenditure')
router.register(r'fixed-expenditure', FixedExpenditureView, basename='fixed_expenditure')
router.register(r'income', IncomeView, basename='income')
router.register(r'payroll', PayrollView, basename='payroll')
router.register(r'pledge', PledgeView, basename='pledge')
router.register(r'tithes', TitheView, basename='tithes')

# ADMIN URLS
router.register(r'assets-tracker', AssetAdminView, basename='admin_assets')
router.register(r'income-tracker', IncomeAdminView, basename='admin_income')
router.register(
    r'expenditure-tracker', ExpenditureAdminView, basename='admin_expenditure'
)


urlpatterns = [
    path('', include(router.urls)),
]
