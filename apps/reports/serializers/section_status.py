from rest_framework import serializers
from apps.reports.models.section_status import ReportSectionStatus

class ReportSectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = ReportSectionStatus
        fields = [
            "id",
            "report",
            "section",
            "status",
            "skip_reason",
            "skip_notes",
            "skipped_by",
            "skipped_at",
            "no_activity_confirmed_by",
            "no_activity_confirmed_at",
            "no_activity_note",
            "started_by",
            "started_at",
            "completed_by",
            "completed_at",
            "follow_up_status",
            "follow_up_notes",
            "follow_up_assigned_to",
            "created_at",
            "updated_at",
        ]
