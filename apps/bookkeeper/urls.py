from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.bookkeeper.views import (
    AssetView,
    ExpenditureView,
    FinanceYearlySummaryView,
    MonthlyIncomeSummaryView,
    RegularExpenditureView,
    IncomeView,
    TitheViewSet,
    FinanceSummaryView
)
from apps.bookkeeper.views.overhead import OverheadViewSet
from apps.bookkeeper.views.revenue import RevenueViewSet

router = SimpleRouter()

router.register(r'assets', AssetView, basename='assets')
router.register(r'expenditure', ExpenditureView, basename='expenditure')
router.register(r'regular_expenditure', RegularExpenditureView, basename='regular_expenditure')
router.register(r'income', IncomeView, basename='income')
router.register(r'tithes', TitheViewSet, basename='tithes')
router.register(r'monthly', MonthlyIncomeSummaryView, basename="monthly")
router.register(r'revenue', RevenueViewSet, basename="revenue")
router.register(r'overhead', OverheadViewSet, basename="overhead")

urlpatterns = [
    path('', include(router.urls)), 
    path("finance/monthly-summary/", FinanceSummaryView.as_view(), name="finance-monthly-summary"),
    path("finance/yearly/", FinanceYearlySummaryView.as_view(), name="finance-yearly"),
]
