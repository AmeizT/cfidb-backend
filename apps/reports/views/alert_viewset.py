from rest_framework import viewsets
from rest_framework.decorators import action
from apps.reports.models.alerts import ComplianceAlert
# from apps.reports.serializers import ComplianceAlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = ComplianceAlert.objects.all()
    serializer_class = None

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.acknowledge()
        return Response({"status": "acknowledged"})


    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolve()
        return Response({"status": "resolved"})