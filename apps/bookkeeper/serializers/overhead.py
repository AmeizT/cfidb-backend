from rest_framework import serializers
from apps.bookkeeper.models import Overhead, OverheadType
from apps.bookkeeper.category_matching import normalize_financial_category_name
from apps.bookkeeper.serializers.expenses import ExpenditureSerializer

class OverheadTypeSerializer(serializers.ModelSerializer):
    kind = serializers.SerializerMethodField()
    is_custom = serializers.SerializerMethodField()
    usage_count = serializers.IntegerField(read_only=True, required=False)
    standard_category = serializers.SerializerMethodField()
    standard_category_id = serializers.PrimaryKeyRelatedField(
        source="standard_category",
        queryset=OverheadType.objects.filter(is_global=True, assembly__isnull=True, is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = OverheadType
        fields = [
            "id", "name", "normalized_name", "kind", "is_global", "is_custom",
            "is_required", "is_active", "assembly", "reporting_group",
            "standard_category", "standard_category_id", "usage_count",
            "needs_review", "created_at",
        ]
        read_only_fields = [
            "assembly", "normalized_name", "kind", "is_global", "is_custom",
            "usage_count", "created_at",
        ]

    def get_kind(self, obj):
        return "overhead"

    def get_is_custom(self, obj):
        return not obj.is_global

    def get_standard_category(self, obj):
        if not obj.standard_category_id:
            return None
        category = obj.standard_category
        return {
            "id": category.pk,
            "name": category.name,
            "reporting_group": category.reporting_group,
        }

    def validate_name(self, value):
        normalized = normalize_financial_category_name(value)
        if not normalized:
            raise serializers.ValidationError("Enter an overhead type name.")
        assembly = self.context.get("assembly")
        if assembly and OverheadType.objects.filter(
            assembly=assembly, normalized_name=normalized,
        ).exists():
            raise serializers.ValidationError("This overhead type already exists for the active assembly.")
        return value.strip()

    def validate(self, attrs):
        standard = attrs.get("standard_category")
        needs_review = attrs.get("needs_review", False)
        if not standard and not needs_review:
            raise serializers.ValidationError({
                "standard_category_id": "Choose a reporting category or mark this type for review."
            })
        return attrs

class OverheadSerializer(serializers.ModelSerializer):
    # Display the overhead_type name in responses
    overhead_type = serializers.StringRelatedField(read_only=True)
    
    # Write-only field for creating custom or selecting existing types
    overhead_type_name = serializers.CharField(write_only=True)

    class Meta:
        model = Overhead
        fields = [
            "id",
            "amount",
            "notes",
            "timestamp",
            "assembly",            # read-only in the frontend; auto-assigned
            "report",              # read-only; auto-assigned
            "overhead_type",
            "overhead_type_name",
        ]
        read_only_fields = ["assembly", "report", "overhead_type"]

    def create(self, validated_data):
        """
        Create a single Overhead instance.
        Assembly is taken from request.user.church.
        OverheadType is created/fetched by name.
        """
        request = self.context["request"]
        assembly = request.user.church

        # Extract custom overhead type name
        overhead_type_name = validated_data.pop("overhead_type_name")

        # Get or create the overhead type
        normalized_name = normalize_financial_category_name(overhead_type_name)
        overhead_type = OverheadType.objects.filter(
            assembly=assembly, normalized_name=normalized_name,
        ).first()
        if overhead_type is None:
            overhead_type = OverheadType.objects.create(
                assembly=assembly, name=overhead_type_name,
                is_global=False, needs_review=True, created_by=request.user,
            )

        # Create the overhead instance
        overhead = Overhead.objects.create(
            assembly=assembly,
            overhead_type=overhead_type,
            **validated_data
        )

        return overhead

    def to_internal_value(self, data):
        """
        Handles batch creation gracefully.
        DRF automatically calls this per item if many=True is set.
        """
        return super().to_internal_value(data)


class ReportOverheadSerializer(serializers.Serializer):
    overheads = serializers.SerializerMethodField()
    variables = serializers.SerializerMethodField()
    total_overhead = serializers.SerializerMethodField()
    total_variable = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()
 
    def get_overheads(self, obj):
        overhead = obj.overhead_set.all()  # matches your related_name
        return OverheadSerializer(overhead, many=True).data

    def get_variables(self, obj):
        variable = obj.variable_expenditure_set.all()
        return ExpenditureSerializer(variable, many=True).data

    def get_total_overhead(self, obj):
        return sum(f.amount for f in obj.overhead_set.all())

    def get_total_variable(self, obj):
        return sum(v.total for v in obj.variable_expenditure_set.all())

    def get_grand_total(self, obj):
        return self.get_total_overhead(obj) + self.get_total_variable(obj)
    






    
