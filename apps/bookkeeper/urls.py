from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.bookkeeper.views import (
    AssetView,
    CreateTitheView,
    ExpenditureView,
    MonthlyIncomeSummaryView,
    RegularExpenditureView,
    IncomeView,
    PayrollView,
    PledgeView,
    RemittanceView,
    RemittanceDataView,
    ShortfallPaymentView,
    TitheView,
)

router = DefaultRouter()

router.register(r'assets', AssetView, basename='assets')
router.register(r'expenditure', ExpenditureView, basename='expenditure')
router.register(r'regular_expenditure', RegularExpenditureView, basename='regular_expenditure')
router.register(r'income', IncomeView, basename='income')
router.register(r'payroll', PayrollView, basename='payroll')
router.register(r'pledge', PledgeView, basename='pledge')
router.register(r'create-tithe', CreateTitheView, basename='create_tithe')
router.register(r'tithes', TitheView, basename='tithes')
router.register(r'remittance', RemittanceView, basename='remittance')
router.register(r'get-remittance', RemittanceDataView, basename='remittance_data')
router.register(r'shortfall', ShortfallPaymentView, basename='shortfall')
router.register(r'monthly', MonthlyIncomeSummaryView, basename="monthly")

urlpatterns = [
    path('', include(router.urls)),
]
