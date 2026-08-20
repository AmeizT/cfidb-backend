from rest_framework import serializers
from apps.reports.models.alerts import ComplianceAlert


class ComplianceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAlert
        fields = [
            "id",
            "assembly",
            "zone",
            "type",
            "level",
            "title",
            "message",
            "status",
            "metadata",
            "created_at",
            "acknowledged_at",
            "resolved_at",
        ]