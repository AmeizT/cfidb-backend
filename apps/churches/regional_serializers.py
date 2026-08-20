from rest_framework import serializers

from apps.churches.models import Church
from apps.users.models import User


class RegionalChurchSerializer(serializers.ModelSerializer):
    zone_name = serializers.SerializerMethodField()
    region_id = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    primary_currency = serializers.CharField(source="currency", read_only=True)
    total_members = serializers.SerializerMethodField()
    assigned_pastors_count = serializers.SerializerMethodField()
    assigned_pastors = serializers.SerializerMethodField()
    pastor_names = serializers.SerializerMethodField()

    class Meta:
        model = Church
        fields = (
            "id",
            "uuid",
            "public_id",
            "code",
            "name",
            "zone",
            "zone_name",
            "region_id",
            "region_name",
            "description",
            "address",
            "city",
            "province",
            "country",
            "country_code",
            "locale",
            "currency",
            "primary_currency",
            "phone_number",
            "email",
            "status",
            "avatar",
            "avatar_fallback",
            "total_members",
            "assigned_pastors_count",
            "assigned_pastors",
            "pastor_names",
            "created_at",
            "updated_at",
        )

    def get_zone_name(self, obj):
        return obj.zone.name if obj.zone else None

    def get_region_id(self, obj):
        if obj.zone and obj.zone.region:
            return obj.zone.region_id
        return None

    def get_region_name(self, obj):
        if obj.zone and obj.zone.region:
            return obj.zone.region.name
        return None

    def get_total_members(self, obj):
        total_members_count = getattr(obj, "total_members_count", None)

        if total_members_count is not None:
            return total_members_count

        return obj.total_members

    def get_assigned_pastors_count(self, obj):
        assigned_pastors_count = getattr(obj, "assigned_pastors_count", None)

        if assigned_pastors_count is not None:
            return assigned_pastors_count

        return obj.assigned_pastors.count()

    def get_assigned_pastors(self, obj):
        return [
            {
                "id": pastor.id,
                "full_name": pastor.full_name,
                "email": pastor.email,
            }
            for pastor in obj.assigned_pastors.all()
        ]

    def get_pastor_names(self, obj):
        return ", ".join(
            pastor.full_name
            for pastor in obj.assigned_pastors.all()
            if pastor.full_name
        )


class RegionalUserSerializer(serializers.ModelSerializer):
    roles = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    role_names = serializers.SerializerMethodField()
    church_id = serializers.SerializerMethodField()
    church_name = serializers.SerializerMethodField()
    church_code = serializers.SerializerMethodField()
    church_country = serializers.SerializerMethodField()
    zone_id = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    region_id = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()
    full_name = serializers.ReadOnlyField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "user_id",
            "full_name",
            "first_name",
            "last_name",
            "username",
            "email",
            "roles",
            "role_names",
            "church_id",
            "church_name",
            "church_code",
            "church_country",
            "zone_id",
            "zone_name",
            "region_id",
            "region_name",
            "avatar",
            "avatar_fallback",
            "last_active",
            "is_active",
            "status",
            "is_onboarded",
            "created_at",
            "updated_at",
        )

    def get_role_names(self, obj):
        return ", ".join(role.name for role in obj.roles.all())

    def get_church_id(self, obj):
        return obj.church_id

    def get_church_name(self, obj):
        return obj.church.name if obj.church else None

    def get_church_code(self, obj):
        return obj.church.code if obj.church else None

    def get_church_country(self, obj):
        return obj.church.country if obj.church else None

    def get_zone_id(self, obj):
        if obj.church and obj.church.zone:
            return obj.church.zone_id
        return None

    def get_zone_name(self, obj):
        if obj.church and obj.church.zone:
            return obj.church.zone.name
        return None

    def get_region_id(self, obj):
        if obj.church and obj.church.zone and obj.church.zone.region:
            return obj.church.zone.region_id
        return None

    def get_region_name(self, obj):
        if obj.church and obj.church.zone and obj.church.zone.region:
            return obj.church.zone.region.name
        return None

    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"
