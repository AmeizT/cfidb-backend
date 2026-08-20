
from rest_framework import serializers
from apps.reports.models.compliance import AssemblyCompliance, ZoneCompliance

class AssemblyComplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssemblyCompliance
        fields = "__all__"


class ZoneComplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneCompliance
        fields = "__all__"