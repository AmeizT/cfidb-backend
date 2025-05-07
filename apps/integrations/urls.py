from rest_framework.routers import DefaultRouter
from apps.integrations.views import IntegrationProviderViewSet, IntegrationViewSet

router = DefaultRouter()
router.register(r'integration-providers', IntegrationProviderViewSet, basename='integration_providers')
router.register(r'integrations', IntegrationViewSet, basename='integration')

urlpatterns = router.urls