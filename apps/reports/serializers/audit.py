from rest_framework import serializers
from apps.reports.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    model = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "model",
            "object_id",
            "action",
            "description",
            "old_data",
            "new_data",
            "timestamp",
        ]
        read_only_fields = fields

    def get_model(self, obj):
        return obj.content_type.model
