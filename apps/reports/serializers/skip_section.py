from rest_framework import serializers
from apps.reports.models.section_status import ReportSectionStatus


class SkipSectionSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=ReportSectionStatus.SkipReason.choices)
    notes = serializers.CharField()