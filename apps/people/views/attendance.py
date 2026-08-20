from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from apps.reports.models import AuditLog
from apps.people.models import Attendance
from apps.people.serializers.attendance import (
    AttendanceSerializer,
    AttendanceBatchEntrySerializer,
    AttendanceWorkbenchSerializer,
)
from apps.uploads.mixins import UploadExcelMixin
from apps.people.mixins import AttendanceTemplateMixin, AuditMixin
from apps.shared.mixins import AssemblyScopedQueryMixin, BulkCreateMixin, SoftDeleteMixin
from apps.shared.mixins.prevent_deleted_updates import PreventDeletedUpdatesMixin
from django_filters.rest_framework import DjangoFilterBackend
from apps.people.filters.attendance_filter import AttendanceFilter
from apps.shared.mixins.soft_delete import SoftDeleteQueryMixin
from apps.bookkeeper.services.manual_entry import BatchEntryValidationError, resolve_report, validate_dates
from apps.bookkeeper.views.batch import batch_error_response, parse_batch_payload, validate_batch_entries

# class AttendanceViewSet(
#     ChurchScopedQueryMixin,
#     UploadExcelMixin,
#     AuditMixin,
#     SoftDeleteMixin,
#     AttendanceTemplateMixin,
#     BulkCreateMixin,
#     ModelViewSet,
# ):
#     serializer_class = AttendanceSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     upload_service_class = AttendanceUploadService

#     def get_object(self):
#         queryset = self.filter_queryset(self.get_queryset())

#         obj = get_object_or_404(
#             queryset,
#             pk=self.kwargs["pk"]
#         )

#         print("OBJECT:", obj)

#         return obj


#     def list(self, request, *args, **kwargs):
#         queryset = Attendance.objects.all()
#         # queryset = self.filter_queryset(self.get_queryset())

#         first = queryset.first()
#         monthly_summary = None

#         if first:
#             monthly_summary = get_monthly_summary(
#                 assembly=first.assembly,
#                 year=first.timestamp.year,
#                 month=first.timestamp.month,
#             )

#         serializer = self.serializer_class(
#             queryset,
#             many=True,
#             context={
#                 **self.get_serializer_context(),
#                 "monthly_summary": monthly_summary
#             }
#         )

#         return Response(serializer.data)
    


#     def create(self, request, *args, **kwargs):
#         is_many = isinstance(request.data, list)
#         serializer = self.get_serializer(data=request.data, many=is_many)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

#     def perform_create(self, serializer):
#         with transaction.atomic():
#             instances = serializer.save()
#             if not isinstance(instances, list):
#                 instances = [instances]

#             for instance in instances:
#                 was_created = serializer.context.get("was_created", True)
#                 old_data = getattr(instance, "_capture_old_data", lambda: None)()
#                 action = AuditLog.Action.CREATE if was_created else AuditLog.Action.UPDATE
#                 description = (
#                     f"{instance.service_type} service | "
#                     f"Headcount: {instance.headcount} | "
#                     f"New Converts: {instance.new_converts}"
#                 )
#                 instance.log_audit(user=self.request.user, action=action, old_data=old_data, description=description)

#     def perform_update(self, serializer):
#         instance = serializer.instance
#         old_data = getattr(instance, "_capture_old_data", lambda: None)()
#         updated_instance = serializer.save()
#         description = (
#             f"{updated_instance.service_type} service updated | "
#             f"Headcount: {updated_instance.headcount} | "
#             f"New Converts: {updated_instance.new_converts}"
#         )
#         updated_instance.log_audit(user=self.request.user, action=AuditLog.Action.UPDATE, old_data=old_data, description=description)

    
class AttendanceViewSet(
    AssemblyScopedQueryMixin,
    PreventDeletedUpdatesMixin,
    UploadExcelMixin,
    AuditMixin,
    AttendanceTemplateMixin,
    SoftDeleteMixin,
    SoftDeleteQueryMixin,
    BulkCreateMixin,
    ModelViewSet,
):
    queryset = Attendance.objects.select_related(
        "assembly",
        "homecell",
        "report",
    ).all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AttendanceFilter

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        payload, error = parse_batch_payload(request)
        if error:
            return error
        entries, error = validate_batch_entries(AttendanceBatchEntrySerializer, payload["entries"], request)
        if error:
            return error
        assembly = getattr(request.user, "church", None)
        if assembly is None:
            return Response({"message": "An active assembly is required."}, status=403)
        saved = []
        current_index = 0
        try:
            validate_dates(entries, payload["period"], "timestamp")
            with transaction.atomic():
                report = resolve_report(
                    assembly=assembly,
                    period=payload["period"],
                    report_id=payload.get("report"),
                )
                errors = {}
                seen = {}
                service_default = Attendance._meta.get_field("service_type").get_default()
                for index, attrs in enumerate(entries):
                    record_id = attrs.get("id")
                    homecell = attrs.get("homecell")
                    key = (
                        attrs["timestamp"],
                        attrs.get("service_type", service_default),
                        getattr(homecell, "pk", None),
                    )
                    if key in seen:
                        errors[str(index)] = {"non_field_errors": [f"Duplicates row {seen[key] + 1}."]}
                    else:
                        seen[key] = index
                    conflict = Attendance.objects.filter(
                        assembly=assembly,
                        timestamp=key[0],
                        service_type=key[1],
                        homecell_id=key[2],
                        is_deleted=False,
                    ).exclude(pk=record_id).first()
                    if conflict:
                        errors[str(index)] = {"non_field_errors": ["Attendance already exists for this week and service."]}
                    if record_id and not Attendance.objects.filter(
                        pk=record_id,
                        assembly=assembly,
                        report=report,
                    ).exists():
                        errors[str(index)] = {"id": ["Saved attendance is outside the active report or assembly."]}
                if errors:
                    raise BatchEntryValidationError({"entries": errors})

                for current_index, attrs in enumerate(entries):
                    record_id = attrs.pop("id", None)
                    if record_id:
                        instance = Attendance.objects.select_for_update().get(pk=record_id, assembly=assembly, report=report)
                        for field, value in attrs.items():
                            setattr(instance, field, value)
                    else:
                        instance = Attendance(assembly=assembly, report=report, **attrs)
                    instance._current_user = request.user
                    instance.full_clean()
                    instance.save()
                    saved.append(instance)
                report.refresh_from_db()
        except BatchEntryValidationError as exc:
            return batch_error_response(exc)
        except IntegrityError:
            return Response({"message": "Some entries are invalid.", "errors": {"entries": {str(current_index): {"non_field_errors": ["Attendance conflicts with an existing record."]}}}}, status=400)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
            return Response({"message": "Some entries are invalid.", "errors": {"entries": {str(current_index): detail}}}, status=400)
        return Response({
            "count": len(saved),
            "records": AttendanceSerializer(saved, many=True, context=self.get_serializer_context()).data,
            "report_totals": {
                "report": report.pk if report else None,
                "attendance_total": report.attendance_total if report else 0,
                "total_adults": report.total_adults if report else 0,
                "total_visitors": report.total_visitors if report else 0,
                "total_new_converts": report.total_new_converts if report else 0,
                "total_baptisms": report.total_baptisms if report else 0,
            },
        }, status=201)

    def get_delete_description(self, instance):
        return (
            f"{instance.service_type} service soft deleted | "
            f"Headcount: {instance.headcount} | "
            f"New Converts: {instance.total_new_converts}"
        )

    def get_restore_description(self, instance):
        return (
            f"{instance.service_type} service restored | "
            f"Headcount: {instance.headcount} | "
            f"New Converts: {instance.total_new_converts}"
        )

    def _get_workbench_duplicate_key(self, assembly, attrs):
        service_type = attrs.get(
            "service_type",
            Attendance._meta.get_field("service_type").get_default(),
        )
        homecell = attrs.get("homecell")

        return (
            getattr(assembly, "id", assembly),
            attrs.get("timestamp"),
            service_type,
            getattr(homecell, "id", None),
        )

    def _format_row_errors(self, serializer_errors):
        if not isinstance(serializer_errors, list):
            return []

        formatted = []
        for index, errors in enumerate(serializer_errors):
            if errors:
                formatted.append({
                    "index": index,
                    "errors": errors,
                })

        return formatted

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create_workbench(self, request):
        records = request.data.get("records")
        idempotency_key = request.data.get("idempotency_key")
        user = request.user
        assembly = getattr(user, "church", None)

        if not assembly:
            return Response(
                {"detail": "An authenticated assembly is required to create attendance."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not isinstance(records, list) or not records:
            return Response(
                {"detail": "records must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = None
        if idempotency_key:
            cache_key = (
                f"workbench:attendance:{getattr(user, 'id', 'anonymous')}:"
                f"{getattr(assembly, 'id', 'assembly')}:{idempotency_key}"
            )
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)

        serializer = AttendanceWorkbenchSerializer(
            data=records,
            many=True,
            context={"request": request},
        )

        if not serializer.is_valid():
            return Response(
                {
                    "detail": "Nothing was saved. Fix the highlighted records and try again.",
                    "errors": self._format_row_errors(serializer.errors),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        row_errors = []
        seen_keys = {}
        service_default = Attendance._meta.get_field("service_type").get_default()

        for index, attrs in enumerate(serializer.validated_data):
            key = self._get_workbench_duplicate_key(assembly, attrs)

            if key in seen_keys:
                first_index = seen_keys[key]
                row_errors.append({
                    "index": index,
                    "errors": {
                        "non_field_errors": [
                            f"Duplicates preview row {first_index + 1}."
                        ]
                    },
                })
            else:
                seen_keys[key] = index

            conflict = Attendance.objects.filter(
                assembly=assembly,
                timestamp=attrs.get("timestamp"),
                service_type=attrs.get("service_type", service_default),
                homecell=attrs.get("homecell"),
                is_deleted=False,
            ).first()

            if conflict:
                row_errors.append({
                    "index": index,
                    "errors": {
                        "non_field_errors": [
                            f"Attendance already exists for this date and service (ID: {conflict.id})."
                        ]
                    },
                    "existing_record_id": conflict.id,
                })

        if row_errors:
            return Response(
                {
                    "detail": "Nothing was saved. Fix the highlighted records and try again.",
                    "errors": row_errors,
                },
                status=status.HTTP_409_CONFLICT,
            )

        created = []

        try:
            with transaction.atomic():
                for attrs in serializer.validated_data:
                    instance = Attendance.objects.create(
                        assembly=assembly,
                        **attrs,
                    )
                    instance.log_audit(
                        user=user,
                        action=AuditLog.Action.CREATE,
                        description=(
                            f"Workbench attendance created | "
                            f"{instance.service_type} service | "
                            f"Headcount: {instance.headcount}"
                        ),
                    )
                    created.append(instance)
        except IntegrityError:
            return Response(
                {
                    "detail": "Nothing was saved. One or more records conflict with existing attendance.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        response_data = {
            "count": len(created),
            "ids": [instance.id for instance in created],
            "records": AttendanceSerializer(
                created,
                many=True,
                context=self.get_serializer_context(),
            ).data,
        }

        if cache_key:
            cache.set(cache_key, response_data, timeout=60 * 60)

        return Response(response_data, status=status.HTTP_201_CREATED)

    
