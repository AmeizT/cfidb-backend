from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.churches.models import Church
from apps.people.models import (
    FormerMember,
    Household,
    HouseholdMember,
    HouseholdRole,
)


class FormerMemberSerializer(serializers.ModelSerializer):
    member_full_name = serializers.CharField(source="member.full_name", read_only=True)
    former_assembly = serializers.IntegerField(source="assembly_id", read_only=True)
    former_assembly_name = serializers.CharField(source="assembly.name", read_only=True)
    current_assembly = serializers.IntegerField(source="current_assembly.id", read_only=True, allow_null=True)
    current_assembly_name = serializers.CharField(source="current_assembly.name", read_only=True, allow_null=True)
    has_been_readmitted = serializers.BooleanField(read_only=True)

    class Meta:
        model = FormerMember
        fields = [
            "id", "member", "member_full_name", "former_assembly", "former_assembly_name",
            "joined_on", "ended_on", "end_reason", "end_notes", "transfer",
            "current_assembly", "current_assembly_name", "has_been_readmitted",
        ]
        read_only_fields = fields


class FormerMemberDetailSerializer(FormerMemberSerializer):
    member_key = serializers.CharField(source="member.member_key", read_only=True)
    phone_number = serializers.CharField(source="member.phone_number", read_only=True)
    email = serializers.CharField(source="member.email", read_only=True)
    avatar = serializers.ImageField(source="member.avatar", read_only=True, allow_null=True)
    avatar_fallback = serializers.CharField(source="member.avatar_fallback", read_only=True)
    member_since = serializers.DateField(source="member.membersince", read_only=True, allow_null=True)
    household_name = serializers.SerializerMethodField()

    class Meta(FormerMemberSerializer.Meta):
        fields = FormerMemberSerializer.Meta.fields + [
            "member_key", "phone_number", "email", "avatar", "avatar_fallback",
            "member_since", "household_name",
        ]

    def get_household_name(self, obj):
        membership = obj.member.household_memberships.filter(left_on__isnull=True).select_related("household").first()
        return membership.household.name if membership else None


class FormerMemberReadmitSerializer(serializers.Serializer):
    assembly = serializers.PrimaryKeyRelatedField(
        queryset=Church.objects.all(),
        required=False,
    )
    joined_on = serializers.DateField()
    household = serializers.PrimaryKeyRelatedField(queryset=Household.objects.all(), required=False)
    household_role = serializers.ChoiceField(choices=HouseholdRole.choices, required=False)
    make_primary_contact = serializers.BooleanField(required=False, default=False)


class HouseholdMemberSerializer(serializers.ModelSerializer):
    member_full_name = serializers.CharField(source="member.full_name", read_only=True)
    household_name = serializers.CharField(source="household.name", read_only=True)

    class Meta:
        model = HouseholdMember
        fields = [
            "id", "household", "household_name", "member", "member_full_name", "role",
            "is_primary_contact", "joined_on", "left_on", "notes", "created_by", "updated_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["left_on", "created_by", "updated_by", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        household = attrs.get("household", getattr(instance, "household", None))
        member = attrs.get("member", getattr(instance, "member", None))
        if household and member and household.assembly_id != member.assembly_id:
            raise serializers.ValidationError({"member": "Member and household must be in the same assembly."})
        if household and household.status == "closed" and not getattr(instance, "left_on", None):
            raise serializers.ValidationError({"household": "A closed household cannot receive members."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        try:
            return HouseholdMember.objects.create(created_by=user, **validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.updated_by = self.context["request"].user
        try:
            instance.save()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return instance


class HouseholdSerializer(serializers.ModelSerializer):
    active_member_count = serializers.IntegerField(read_only=True)
    primary_contact_id = serializers.IntegerField(source="primary_contact.id", read_only=True, allow_null=True)
    head_of_household = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = [
            "id", "assembly", "household_key", "name", "status", "phone_number",
            "secondary_phone_number", "email", "address", "address_line2", "city", "province",
            "country", "notes", "active_member_count", "primary_contact_id", "created_by",
            "updated_by", "created_at", "updated_at", "head_of_household", "location", "contact",
        ]
        read_only_fields = ["household_key", "created_by", "updated_by", "created_at", "updated_at"]
        extra_kwargs = {"assembly": {"required": False}}

    def get_head_of_household(self, obj):
        membership = obj.primary_contact_membership
        if membership is None:
            prefetched = getattr(obj, "_prefetched_objects_cache", {}).get("household_memberships")
            if prefetched is not None:
                membership = next(
                    (item for item in prefetched if item.left_on is None and item.role == "head"),
                    None,
                )
            else:
                membership = obj.household_memberships.filter(
                    left_on__isnull=True,
                    role="head",
                ).select_related("member").first()
        return membership.member.full_name if membership else None

    def get_location(self, obj):
        return ", ".join(part for part in (obj.address, obj.city, obj.province, obj.country) if part)

    def get_contact(self, obj):
        return obj.phone_number or obj.email or ""

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        try:
            return super().create(validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context["request"].user
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc


class HouseholdMemberSummarySerializer(serializers.ModelSerializer):
    member_key = serializers.CharField(source="member.member_key", read_only=True)
    member_full_name = serializers.CharField(source="member.full_name", read_only=True)
    avatar = serializers.ImageField(source="member.avatar", read_only=True, allow_null=True)
    avatar_fallback = serializers.CharField(source="member.avatar_fallback", read_only=True)
    age = serializers.IntegerField(source="member.age", read_only=True)

    class Meta:
        model = HouseholdMember
        fields = [
            "id", "member", "member_key", "member_full_name", "avatar",
            "avatar_fallback", "age", "role", "is_primary_contact", "joined_on",
        ]
        read_only_fields = fields


class HouseholdDetailSerializer(HouseholdSerializer):
    assembly_name = serializers.CharField(source="assembly.name", read_only=True)
    adult_count = serializers.IntegerField(read_only=True)
    minor_count = serializers.IntegerField(read_only=True)
    members = serializers.SerializerMethodField()

    class Meta(HouseholdSerializer.Meta):
        fields = HouseholdSerializer.Meta.fields + [
            "assembly_name", "adult_count", "minor_count", "members",
        ]

    def get_members(self, obj):
        memberships = [
            membership
            for membership in obj.household_memberships.all()
            if membership.left_on is None
        ]
        return HouseholdMemberSummarySerializer(
            memberships,
            many=True,
            context=self.context,
        ).data
