from decimal import Decimal

from rest_framework import serializers

from .models import JethroConversation, JethroMessage


class JethroMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JethroMessage
        fields = ("role", "content", "structured_content", "created_at")


class JethroConversationSerializer(serializers.ModelSerializer):
    messages = JethroMessageSerializer(many=True, read_only=True)

    class Meta:
        model = JethroConversation
        fields = ("public_id", "title", "created_at", "updated_at", "is_archived", "messages")
        read_only_fields = ("public_id", "title", "created_at", "updated_at", "messages")


class JethroMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField(trim_whitespace=True)
    conversation_id = serializers.CharField(max_length=21, required=False, allow_blank=False)

    def validate_message(self, value):
        from django.conf import settings

        if len(value) > settings.JETHRO_MAX_MESSAGE_LENGTH:
            raise serializers.ValidationError(
                f"Messages must be {settings.JETHRO_MAX_MESSAGE_LENGTH} characters or fewer."
            )
        return value


class SearchMembersArgumentsSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=120, trim_whitespace=True)
    status = serializers.CharField(max_length=40, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=10)


class MembershipSummaryArgumentsSerializer(serializers.Serializer):
    period = serializers.ChoiceField(
        choices=("current_month", "current_year", "all_time"), default="all_time"
    )


class ReportStatusArgumentsSerializer(serializers.Serializer):
    period = serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$")
    report_type = serializers.CharField(max_length=50, required=False)


class PrepareTitheArgumentsSerializer(serializers.Serializer):
    member_query = serializers.CharField(max_length=120, trim_whitespace=True)
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    payment_method = serializers.CharField(max_length=50, trim_whitespace=True)
    payment_date = serializers.DateField(required=False, allow_null=True)
    reference = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )


class TitheMemberSelectionSerializer(serializers.Serializer):
    member_public_id = serializers.CharField(max_length=21)
