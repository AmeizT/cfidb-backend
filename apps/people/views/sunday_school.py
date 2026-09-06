from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.people.filters.sunday_school import SundaySchoolAttendanceFilter
from apps.people.models import SundaySchoolAttendance
from apps.people.serializers import (
    SundaySchoolAttendanceApprovalSerializer,
    SundaySchoolAttendanceSerializer,
)
from apps.people.mixins import SundaySchoolTemplateMixin
from apps.reports.models.audit import AuditLog
from apps.uploads.mixins import UploadExcelMixin
from apps.uploads.services import SundaySchoolAttendanceUploadService
from apps.shared.mixins.prevent_deleted_updates import PreventDeletedUpdatesMixin
from apps.shared.mixins.soft_delete import SoftDeleteMixin


class SundaySchoolAttendanceViewSet(
    UploadExcelMixin,
    SundaySchoolTemplateMixin,
    PreventDeletedUpdatesMixin,
    SoftDeleteMixin,
    viewsets.ModelViewSet,
):
    queryset = SundaySchoolAttendance.objects.select_related(
        "assembly",
        "assembly__zone",
        "assembly__zone__region",
        "teacher",
        "reported_by",
        "reviewed_by",
    )
    serializer_class = SundaySchoolAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SundaySchoolAttendanceFilter
    upload_service_class = SundaySchoolAttendanceUploadService

    def get_queryset(self):
        queryset = self.queryset.all()
        user = self.request.user
        queryset = queryset.filter(is_deleted=False)

        if getattr(user, "is_admin", False):
            return queryset

        if getattr(user, "is_region_staff", False):
            regions = user.assigned_regions
            if regions.exists():
                return queryset.filter(assembly__zone__region__in=regions)

        if getattr(user, "is_db_zone_staff", False):
            zones = user.assigned_zones
            if zones.exists():
                return queryset.filter(assembly__zone__in=zones)

        assembly = getattr(user, "church", None)
        if assembly:
            return queryset.filter(assembly=assembly)

        return queryset.none()

    def _audit(self, instance, action, old_data=None, description=None):
        instance.log_audit(
            user=self.request.user,
            action=action,
            old_data=old_data,
            description=description,
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            self._audit(
                instance,
                AuditLog.Action.CREATE,
                description=(
                    f"Sunday School attendance submitted for "
                    f"{instance.get_class_name_display()} on {instance.service_date}"
                ),
            )

    def perform_update(self, serializer):
        instance = serializer.instance
        old_data = instance._capture_old_data()
        updated_instance = serializer.save()
        self._audit(
            updated_instance,
            AuditLog.Action.UPDATE,
            old_data=old_data,
            description=(
                f"Sunday School attendance updated for "
                f"{updated_instance.get_class_name_display()} on {updated_instance.service_date}"
            ),
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        instance = self.get_object()
        old_data = instance._capture_old_data()
        instance.submit(user=request.user)
        self._audit(
            instance,
            AuditLog.Action.UPDATE,
            old_data=old_data,
            description="Sunday School attendance submitted for review.",
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        instance = self.get_object()
        old_data = instance._capture_old_data()
        instance.approve(user=request.user)
        self._audit(
            instance,
            AuditLog.Action.UPDATE,
            old_data=old_data,
            description="Sunday School attendance approved.",
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        instance = self.get_object()
        old_data = instance._capture_old_data()
        instance.reject(user=request.user)
        self._audit(
            instance,
            AuditLog.Action.UPDATE,
            old_data=old_data,
            description="Sunday School attendance rejected.",
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["post"], url_path="review")
    def review(self, request, pk=None):
        serializer = SundaySchoolAttendanceApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]
        instance = self.get_object()
        old_data = instance._capture_old_data()

        if action_name == "approve":
            instance.approve(user=request.user)
        elif action_name == "reject":
            instance.reject(user=request.user)
        else:
            instance.mark_under_review(user=request.user)

        self._audit(
            instance,
            AuditLog.Action.UPDATE,
            old_data=old_data,
            description=f"Sunday School attendance marked as {instance.get_status_display()}.",
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=["get"], url_path="aggregates")
    def aggregates(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        summary = self._summary(queryset)

        return Response({
            **summary,
            "attendance_by_class": self._grouped_attendance(
                queryset,
                ["class_name"],
                "class_name",
                label_from_choice=True,
            ),
            "attendance_by_teacher": self._grouped_attendance(
                queryset,
                ["teacher_id", "teacher__first_name", "teacher__last_name"],
                "teacher_id",
            ),
            "attendance_by_assembly": self._grouped_attendance(
                queryset,
                ["assembly_id", "assembly__name"],
                "assembly_id",
            ),
            "attendance_by_zone": self._grouped_attendance(
                queryset,
                ["assembly__zone_id", "assembly__zone__name"],
                "assembly__zone_id",
            ),
            "attendance_by_region": self._grouped_attendance(
                queryset,
                ["assembly__zone__region_id", "assembly__zone__region__name"],
                "assembly__zone__region_id",
            ),
            "generated_at": timezone.now(),
        })

    def _summary(self, queryset):
        totals = queryset.aggregate(
            records=Count("id"),
            boys=Sum("boys"),
            girls=Sum("girls"),
            male_visitors=Sum("male_visitors"),
            female_visitors=Sum("female_visitors"),
            male_first_timers=Sum("male_first_timers"),
            female_first_timers=Sum("female_first_timers"),
            offering=Sum("offering"),
        )

        total_children = self._int(totals["boys"]) + self._int(totals["girls"])
        total_visitors = self._int(totals["male_visitors"]) + self._int(totals["female_visitors"])
        total_first_timers = (
            self._int(totals["male_first_timers"])
            + self._int(totals["female_first_timers"])
        )
        records = self._int(totals["records"])

        return {
            "total_children": total_children,
            "total_visitors": total_visitors,
            "total_first_timers": total_first_timers,
            "average_attendance": round(total_children / records, 2) if records else 0,
            "sunday_school_offering": totals["offering"] or 0,
        }

    def _grouped_attendance(self, queryset, values, id_key, label_from_choice=False):
        rows = queryset.values(*values).annotate(
            records=Count("id"),
            boys=Sum("boys"),
            girls=Sum("girls"),
            male_visitors=Sum("male_visitors"),
            female_visitors=Sum("female_visitors"),
            male_first_timers=Sum("male_first_timers"),
            female_first_timers=Sum("female_first_timers"),
            offering=Sum("offering"),
        )

        grouped_rows = []
        choice_labels = dict(SundaySchoolAttendance._meta.get_field("class_name").choices)

        for row in rows:
            total_children = self._int(row["boys"]) + self._int(row["girls"])
            total_visitors = self._int(row["male_visitors"]) + self._int(row["female_visitors"])
            total_first_timers = (
                self._int(row["male_first_timers"])
                + self._int(row["female_first_timers"])
            )

            grouped_rows.append({
                "id": row.get(id_key) or "unassigned",
                "label": self._group_label(row, values, choice_labels, label_from_choice),
                "records": self._int(row["records"]),
                "total_children": total_children,
                "total_visitors": total_visitors,
                "total_first_timers": total_first_timers,
                "grand_total": total_children + total_visitors + total_first_timers,
                "offering": row["offering"] or 0,
            })

        return grouped_rows

    def _group_label(self, row, values, choice_labels, label_from_choice):
        if label_from_choice:
            return choice_labels.get(row.get("class_name"), "Unassigned")

        name_fields = [field for field in values if field.endswith("__name")]
        if name_fields:
            return row.get(name_fields[0]) or "Unassigned"

        first_name = row.get("teacher__first_name")
        last_name = row.get("teacher__last_name")
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        return full_name or "Unassigned"

    def _int(self, value):
        return int(value or 0)
