from django.db import transaction
from apps.bookkeeper.models import Tithe, GeneratedTitheReceipt
from apps.people.serializers import MemberMinifiedSerializer
from rest_framework import serializers


class GeneratedTitheReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedTitheReceipt
        fields = ["id", "tithe", "receipt_number", "receipt_data", "issued_at", "issued_by", "printed_at", "printed_by", "last_printed_at"]
        read_only_fields = fields


class TitheSerializer(serializers.ModelSerializer):
    receipt_status = serializers.SerializerMethodField()

    def get_receipt_status(self, obj):
        receipt = getattr(obj, "generated_receipt", None)
        return "Printed" if receipt and receipt.printed_at else "Not printed"

    generated_receipt = GeneratedTitheReceiptSerializer(read_only=True)
    receipt_number = serializers.CharField(source="generated_receipt.receipt_number", read_only=True, default=None)
    printed_at = serializers.DateTimeField(source="generated_receipt.printed_at", read_only=True, default=None)

    class Meta:
        model = Tithe
        fields = "__all__"
        read_only_fields = ["assembly", "report"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["member"] = (
            MemberMinifiedSerializer(instance.member).data
            if instance.member_id
            else None
        )
        return data


class BulkTitheSerializer(serializers.ListSerializer):

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        created = []
        for item in validated_data:
            item["assembly"] = user.church
            instance = Tithe(**item)
            instance._current_user = user
            instance.full_clean()
            instance.save()
            created.append(instance)
        return created


class TitheWriteSerializer(TitheSerializer):
    class Meta(TitheSerializer.Meta):
        list_serializer_class = BulkTitheSerializer


        
