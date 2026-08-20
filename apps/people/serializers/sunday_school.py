from decimal import Decimal

from rest_framework import serializers

from apps.people.models import SundaySchoolAttendance
from apps.people.constants import SUNDAY_SCHOOL_START_DATE


class SundaySchoolAttendanceSerializer(serializers.ModelSerializer):
    assembly_name = serializers.CharField(source="assembly.name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True)
    reported_by_name = serializers.CharField(source="reported_by.full_name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.full_name", read_only=True)
    class_label = serializers.CharField(source="get_class_name_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    total_children = serializers.IntegerField(read_only=True)
    total_visitors = serializers.IntegerField(read_only=True)
    total_first_timers = serializers.IntegerField(read_only=True)
    grand_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = SundaySchoolAttendance
        fields = [
            "id",
            "assembly",
            "assembly_name",
            "report",
            "teacher",
            "teacher_name",
            "reported_by",
            "reported_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "service_date",
            "class_name",
            "class_label",
            "boys",
            "girls",
            "male_visitors",
            "female_visitors",
            "male_first_timers",
            "female_first_timers",
            "lesson_title",
            "scripture_reference",
            "offering",
            "remarks",
            "status",
            "status_label",
            "submitted_at",
            "reviewed_at",
            "total_children",
            "total_visitors",
            "total_first_timers",
            "grand_total",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "assembly",
            "report",
            "reported_by",
            "reviewed_by",
            "status",
            "submitted_at",
            "reviewed_at",
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def _request_user(self):
        request = self.context.get("request")
        return getattr(request, "user", None)

    def _request_assembly(self):
        user = self._request_user()
        return getattr(user, "church", None)

    def validate(self, attrs):
        instance = self.instance
        assembly = getattr(instance, "assembly", None) or self._request_assembly()
        teacher = attrs.get("teacher") or getattr(instance, "teacher", None)
        service_date = attrs.get("service_date") or getattr(instance, "service_date", None)
        class_name = attrs.get("class_name") or getattr(instance, "class_name", None)

        if assembly is None:
            raise serializers.ValidationError(
                "An assembly is required to record Sunday School attendance."
            )

        if service_date and service_date < SUNDAY_SCHOOL_START_DATE:
            raise serializers.ValidationError({
                "service_date": (
                    f"Sunday School attendance starts on {SUNDAY_SCHOOL_START_DATE.isoformat()}."
                )
            })

        if teacher and teacher.assembly_id != assembly.id:
            raise serializers.ValidationError({
                "teacher": "Teacher must belong to the same assembly."
            })

        for field in SundaySchoolAttendance.COUNT_FIELDS:
            value = attrs.get(field, getattr(instance, field, 0))
            if value is not None and value < 0:
                raise serializers.ValidationError({
                    field: "Attendance counts cannot be negative."
                })

        offering = attrs.get("offering", getattr(instance, "offering", Decimal("0")))
        if offering is not None and offering < Decimal("0"):
            raise serializers.ValidationError({
                "offering": "Offering cannot be negative."
            })

        if service_date and class_name:
            duplicate = SundaySchoolAttendance.objects.filter(
                assembly=assembly,
                class_name=class_name,
                service_date=service_date,
                is_deleted=False,
            )

            if instance:
                duplicate = duplicate.exclude(pk=instance.pk)

            if duplicate.exists():
                raise serializers.ValidationError(
                    "A Sunday School attendance record already exists for this assembly, class, and service date."
                )

        return attrs

    def create(self, validated_data):
        user = self._request_user()
        assembly = self._request_assembly()

        if assembly is None:
            raise serializers.ValidationError(
                "Authenticated user must belong to an assembly."
            )

        return SundaySchoolAttendance.objects.create(
            assembly=assembly,
            reported_by=user,
            **validated_data,
        )


class SundaySchoolAttendanceApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "under_review"])
