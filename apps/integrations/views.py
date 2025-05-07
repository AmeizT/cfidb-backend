from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.integrations.models import IntegrationProvider, Integration
from apps.integrations.serializers import IntegrationProvider, IntegrationProviderSerializer, IntegrationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

class IntegrationProviderViewSet(viewsets.ModelViewSet):
    queryset = IntegrationProvider.objects.all()
    serializer_class = IntegrationProviderSerializer
    permission_classes = [IsAuthenticated]


class IntegrationViewSet(viewsets.ModelViewSet):
    queryset = Integration.objects.select_related("integration_provider", "user").all()
    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
    
    @action(detail=False, methods=["get"], url_path="connected-apps")
    def connected_apps(self, request):
        integrations = Integration.objects.filter(user=request.user)
        connected_apps = integrations.values_list("integration_provider__name", flat=True).distinct()
        return Response({"connected_apps": list(connected_apps)})