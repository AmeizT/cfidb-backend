from decimal import Decimal

from rest_framework import serializers

from apps.bookkeeper.models import Expenditure, OverheadType, PaymentMethod, RevenueCategory
from apps.people.models import Member


class BatchEnvelopeSerializer(serializers.Serializer):
    period = serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$")
    report = serializers.IntegerField(required=False, allow_null=True)


class TitheBatchEntrySerializer(serializers.Serializer):
    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all(), required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateField()
    receipt = serializers.FileField(required=False, allow_null=True)


class RevenueBatchEntrySerializer(serializers.Serializer):
    category = serializers.PrimaryKeyRelatedField(queryset=RevenueCategory.objects.all())
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    notes = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateField()
    statement = serializers.FileField(required=False, allow_null=True)


class OverheadBatchEntrySerializer(serializers.Serializer):
    overhead_type = serializers.PrimaryKeyRelatedField(queryset=OverheadType.objects.all())
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    notes = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateField()


class ExpenditureBatchEntrySerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Expenditure
        fields = [
            "invoice_number", "invoice_date", "name", "description", "category",
            "supplier", "quantity", "price", "receipt",
        ]
        extra_kwargs = {
            "invoice_number": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True},
            "supplier": {"required": False, "allow_blank": True},
            "receipt": {"required": False, "allow_null": True},
        }
