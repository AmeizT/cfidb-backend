from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reports.views import UnifiedReportViewSet

router = DefaultRouter()
router.register("reports", UnifiedReportViewSet, basename="reports")

urlpatterns = [
    path("", include(router.urls)),
]