from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.bookkeeper.views import (
    AssetView,
    ExpenditureView,
    IncomeView,
    PayrollView,
    AssetAdminView,
    IncomeAdminView,
    ExpenditureAdminView,
)

router = DefaultRouter()

router.register(r"assets", AssetView, basename="assets")
router.register(r"expenditure", ExpenditureView, basename="expenditure")
router.register(r"income", IncomeView, basename="income")
router.register(r"payroll", PayrollView, basename="payroll")

# ADMIN URLS
router.register(r"assets-tracker", AssetAdminView, basename="admin_assets")
router.register(r"income-tracker", IncomeAdminView, basename="admin_income")
router.register(
    r"expenditure-tracker", ExpenditureAdminView, basename="admin_expenditure"
)


urlpatterns = [
    path("", include(router.urls)),
]
