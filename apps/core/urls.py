from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.views import BlogView, DocumentationView, TermsCheckView, AcceptTermsView, TermsView

router = DefaultRouter()

router.register(r"documentation", DocumentationView, basename="documentation")
router.register(r"terms", TermsView, basename="terms")
router.register(r"blogs", BlogView, basename="blogs")   

urlpatterns = [
    path("", include(router.urls)),
    path("terms/check/", TermsCheckView.as_view(), name="terms-check"),
    path("terms/accept/", AcceptTermsView.as_view(), name="terms-accept"),
]