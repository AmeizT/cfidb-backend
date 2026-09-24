from rest_framework import serializers
from django.db import transaction # type: ignore
from apps.people.models import Attendance
from apps.core.serializers import HyperlinkedModelSerializer
from apps.people.services import get_monthly_summary
from drf_spectacular.utils import extend_schema_serializer, extend_schema_field
from apps.reports.services.lifecycle import can_complete_report, can_create_report, get_report_state
from apps.reports.models import AssemblyReport
from apps.reports.services.periods import report_period

@extend_schema_serializer(
    examples=[
        {
            "summary": "Monthly summary example",
            "value": {
                "monthly_summary": {
                    "total_adults": 270,
                    "total_children": 95,
                    "total_visitors": 30,
                    "total_new_converts": 13,
                    "total_baptisms": 6,
                    "total_altar_call": 25,
                    "online_viewers": 110,
                    "volunteers_on_duty": 32,
                    "total_leaders_present": 28,
                    "headcount": 395,
                }
            },
        }
    ], # type: ignore
)


class AttendanceMonthlySummarySerializer(serializers.Serializer):
    total_adults = serializers.IntegerField()
    total_children = serializers.IntegerField()
    total_visitors = serializers.IntegerField()
    total_new_converts = serializers.IntegerField()
    total_baptisms = serializers.IntegerField()
    total_altar_call = serializers.IntegerField()
    online_viewers = serializers.IntegerField()
    volunteers_on_duty = serializers.IntegerField()
    total_leaders_present = serializers.IntegerField()
    headcount = serializers.IntegerField()

class AttendanceSerializer(HyperlinkedModelSerializer):
    app_name = "people"   
    basename = "attendance"

    related_routes = {
        "attendance_url": {
            "app_name": "people",
            "basename": "attendance",
            "lookup": "id",
        },
    }

    headcount = serializers.IntegerField(read_only=True)
    total_children = serializers.IntegerField(source="children", read_only=True)
    assembly_name = serializers.CharField(source="assembly.name", read_only=True)
    homecell_name = serializers.CharField(
        source="homecell.group_name",
        read_only=True,
        allow_null=True,
        default=None,
    )
    report_status = serializers.CharField(
        source="report.status",
        read_only=True,
        allow_null=True,
        default=None,
    )
    report_status_label = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    monthly_summary = serializers.SerializerMethodField()
    legacy = serializers.SerializerMethodField()

    men = serializers.IntegerField(required=False, min_value=0)
    women = serializers.IntegerField(required=False, min_value=0)
    visitor_men = serializers.IntegerField(required=False, min_value=0)
    visitor_women = serializers.IntegerField(required=False, min_value=0)
    new_convert_men = serializers.IntegerField(required=False, min_value=0)
    new_convert_women = serializers.IntegerField(required=False, min_value=0)
    altar_call_men = serializers.IntegerField(required=False, min_value=0)
    altar_call_women = serializers.IntegerField(required=False, min_value=0)
    baptism_men = serializers.IntegerField(required=False, min_value=0)
    baptism_women = serializers.IntegerField(required=False, min_value=0)

    adults = serializers.IntegerField(write_only=True, required=False, min_value=0)
    children = serializers.IntegerField(write_only=True, required=False, min_value=0)
    guest_attendance = serializers.IntegerField(write_only=True, required=False, min_value=0)
    new_converts = serializers.IntegerField(write_only=True, required=False, min_value=0)
    altar_call = serializers.IntegerField(write_only=True, required=False, min_value=0)
    baptisms = serializers.IntegerField(write_only=True, required=False, min_value=0)

    @extend_schema_field(AttendanceMonthlySummarySerializer)  
    def get_monthly_summary(self, obj):
        return self.context.get("monthly_summary", {})

    def get_legacy(self, obj):
        return {
            "adults": obj.adults,
            "guest_attendance": obj.guest_attendance,
            "new_converts": obj.new_converts,
            "altar_call": obj.altar_call,
            "baptisms": obj.baptisms,
        }

    def get_report_status_label(self, obj):
        if obj.report is None:
            return "Unassigned"
        return obj.report.get_status_display()

    def get_can_edit(self, obj):
        return not obj.is_deleted and (
            obj.report is None or obj.report.status == "draft"
        )

    class Meta: # type: ignore
        model = Attendance
        fields = [
            "id",
            "url",
            "links",
            "actions",
            "collection_actions",
            "assembly",
            "assembly_name",
            "report",
            "report_status",
            "report_status_label",
            "can_edit",
            "homecell",
            "homecell_name",
            "service_type",
            "is_special_event",
            "special_event_name",
            "weather",
            "preacher",
            "sermon",
            "scriptures",
            "notes",
            "total_adults",
            "total_children",
            "total_visitors",
            "total_new_converts",
            "total_altar_call",
            "total_baptisms",
            "online_viewers",
            "volunteers_on_duty",
            "total_leaders_present",
            "headcount",
            "legacy",
            "monthly_summary",
            "is_deleted",
            "timestamp",
            "created_at",
            "updated_at",
            "men",
            "women",
            "visitor_men",
            "visitor_women",
            "new_convert_men",
            "new_convert_women",
            "altar_call_men",
            "altar_call_women",
            "baptism_men",
            "baptism_women",
            "adults",
            "children",
            "guest_attendance",
            "new_converts",
            "altar_call",
            "baptisms",
        ]
        read_only_fields = [
            "id",
            "url",
            "links",
            "actions",
            "collection_actions",
            "assembly",
            "assembly_name",
            "report",
            "report_status",
            "report_status_label",
            "can_edit",
            "homecell_name",
            "total_adults",
            "total_children",
            "total_visitors",
            "total_new_converts",
            "total_altar_call",
            "total_baptisms",
            "headcount",
            "legacy",
            "monthly_summary",
            "created_at",
            "updated_at",
        ]

    @transaction.atomic
    def create(self, validated_data):
        # Auto-assign assembly
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if hasattr(user, "church"):
            validated_data["assembly"] = user.church # type: ignore

        # UPSERT logic
        timestamp = validated_data.get("timestamp")
        service_type = validated_data.get("service_type")
        homecell = validated_data.get("homecell")

        instance = Attendance.objects.filter(
            assembly=validated_data["assembly"],
            timestamp=timestamp,
            service_type=service_type,
            homecell=homecell
        ).first()

        if instance:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            self.context["was_created"] = False
            return instance

        instance = Attendance.objects.create(**validated_data)
        self.context["was_created"] = True
        return instance

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        report = getattr(self.instance, "report", None)
        if report is not None and not get_report_state(report, getattr(request, "user", None)).is_editable:
            raise serializers.ValidationError({"detail": "This report is locked for editing."})

        assembly = getattr(self.instance, "assembly", None) or getattr(user, "church", None)
        timestamp = attrs.get("timestamp", getattr(self.instance, "timestamp", None))
        if assembly is not None and timestamp is not None:
            start, end = report_period(timestamp)
            target = AssemblyReport.objects.filter(
                assembly=assembly, period_start=start, period_end=end
            ).first()
            allowed = can_complete_report(user, target) if target else can_create_report(
                user, assembly=assembly, period_start=start
            )
            if not allowed:
                raise serializers.ValidationError({"detail": "This reporting period is not editable."})

        allowed_fields = set(self.fields.keys())
        sent_fields = set(self.initial_data.keys()) # type: ignore
        extra_fields = sent_fields - allowed_fields
        if extra_fields:
            raise serializers.ValidationError(f"Unexpected fields: {extra_fields}")
        return attrs


class AttendanceWorkbenchSerializer(serializers.ModelSerializer):
    """
    Write-only Attendance serializer for Workbench creation.

    It intentionally exposes only fields that are safe for quick entry. Assembly,
    report, audit, soft-delete, and calculated total fields remain server-owned.
    """

    class Meta:
        model = Attendance
        fields = [
            "timestamp",
            "service_type",
            "homecell",
            "is_special_event",
            "special_event_name",
            "weather",
            "preacher",
            "sermon",
            "scriptures",
            "notes",
            "men",
            "women",
            "visitor_men",
            "visitor_women",
            "new_convert_men",
            "new_convert_women",
            "altar_call_men",
            "altar_call_women",
            "baptism_men",
            "baptism_women",
            "online_viewers",
            "volunteers_on_duty",
            "total_leaders_present",
        ]
        extra_kwargs = {
            "timestamp": {"required": True},
            "homecell": {"required": False, "allow_null": True},
        }

    def validate_homecell(self, homecell):
        if homecell is None:
            return homecell

        request = self.context.get("request")
        user = getattr(request, "user", None)
        assembly = getattr(user, "church", None)

        if assembly and getattr(homecell, "church_id", None) != getattr(assembly, "id", None):
            raise serializers.ValidationError(
                "Homecell is outside the authenticated assembly scope."
            )

        return homecell


class AttendanceBatchEntrySerializer(AttendanceWorkbenchSerializer):
    id = serializers.IntegerField(required=False)

    class Meta(AttendanceWorkbenchSerializer.Meta):
        fields = ["id", *AttendanceWorkbenchSerializer.Meta.fields]
