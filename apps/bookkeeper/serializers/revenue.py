from rest_framework import serializers
from apps.bookkeeper.models import Revenue, RevenueCategory
from apps.bookkeeper.category_matching import normalize_financial_category_name

class RevenueSerializer(serializers.ModelSerializer):
    # Display category name in response
    category = serializers.StringRelatedField(read_only=True)

    # Write-only field for creating/selecting category
    category_name = serializers.CharField(write_only=True)

    class Meta:
        model = Revenue
        fields = [
            "id",
            "amount",
            "notes",
            "timestamp",
            "assembly",        # read-only
            "report",          # read-only
            "category",
            "category_name",
            "statement",
        ]
        read_only_fields = ["assembly", "report", "category"]

    def create(self, validated_data):
        request = self.context["request"]
        assembly = request.user.church

        category_name = validated_data.pop("category_name")

        # Get or create category
        normalized_name = normalize_financial_category_name(category_name)
        category = RevenueCategory.objects.filter(
            assembly=assembly, normalized_name=normalized_name,
        ).first()
        if category is None:
            category = RevenueCategory.objects.create(
                assembly=assembly, name=category_name,
                is_standard=False, needs_review=True, created_by=request.user,
            )

        revenue = Revenue.objects.create(
            assembly=assembly,
            category=category,
            **validated_data
        )

        return revenue


class RevenueCategorySerializer(serializers.ModelSerializer):
    kind = serializers.SerializerMethodField()
    is_custom = serializers.SerializerMethodField()
    usage_count = serializers.IntegerField(read_only=True, required=False)
    standard_category = serializers.SerializerMethodField()
    standard_category_id = serializers.PrimaryKeyRelatedField(
        source="standard_category",
        queryset=RevenueCategory.objects.filter(is_standard=True, assembly__isnull=True, is_active=True),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = RevenueCategory
        fields = [
            "id", "name", "normalized_name", "kind", "is_standard", "is_custom",
            "is_active", "assembly", "reporting_group", "standard_category",
            "standard_category_id", "usage_count", "needs_review", "created_at",
        ]
        read_only_fields = [
            "assembly", "normalized_name", "kind", "is_standard", "is_custom",
            "usage_count", "created_at",
        ]

    def get_kind(self, obj):
        return "revenue"

    def get_is_custom(self, obj):
        return not obj.is_standard

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
            raise serializers.ValidationError("Enter a category name.")
        assembly = self.context.get("assembly")
        if assembly and RevenueCategory.objects.filter(
            assembly=assembly, normalized_name=normalized,
        ).exists():
            raise serializers.ValidationError("This category already exists for the active assembly.")
        return value.strip()

    def validate(self, attrs):
        standard = attrs.get("standard_category")
        needs_review = attrs.get("needs_review", False)
        if not standard and not needs_review:
            raise serializers.ValidationError({
                "standard_category_id": "Choose a reporting category or mark this category for review."
            })
        return attrs
