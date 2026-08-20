import calendar
from decimal import Decimal

from django.db.models import Avg, Max, Q, Sum
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.bookkeeper.models import Tithe
from apps.bookkeeper.pagination import StandardPagination
from apps.bookkeeper.serializers import TitheSerializer
from apps.bookkeeper.views.base import FinancialViewSet
from apps.churches.models import Forecast
from apps.reports.models import AuditLog
from apps.reports.serializers import AuditLogSerializer
from apps.uploads.mixins.tithes_template import TitheTemplateMixin
from apps.uploads.services.tithes_upload import TitheUploadService
from apps.uploads.mixins.upload_mixin import UploadExcelMixin
from apps.bookkeeper.serializers import TitheBatchEntrySerializer
from apps.bookkeeper.services import BatchEntryValidationError, create_tithes
from apps.bookkeeper.views.batch import active_assembly_or_error, batch_error_response, parse_batch_payload, validate_batch_entries


class TitheViewSet(
    UploadExcelMixin,
    TitheTemplateMixin,
    FinancialViewSet
):
    queryset = Tithe.objects.all()
    serializer_class = TitheSerializer
    upload_service_class = TitheUploadService
    pagination_class = StandardPagination

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        payload, error = parse_batch_payload(request, file_fields=("receipt",))
        if error:
            return error
        entries, error = validate_batch_entries(TitheBatchEntrySerializer, payload["entries"], request)
        if error:
            return error
        entries = [{**row, "member_id": row["member"].pk if row.get("member") else None} for row in entries]
        try:
            created, totals = create_tithes(
                assembly=assembly, user=request.user, period=payload["period"],
                report_id=payload.get("report"), entries=entries,
            )
        except BatchEntryValidationError as exc:
            return batch_error_response(exc)
        return Response({"count": len(created), "records": self.get_serializer(created, many=True).data, "report_totals": totals}, status=201)

    def get_queryset(self):
        return super().get_queryset().select_related("member", "assembly", "report")

    def _filtered_active_queryset(self):
        queryset = Tithe.all_objects.filter(
            assembly=self.request.user.church, # type: ignore
            is_trash=False,
        ).select_related("member", "assembly", "report")

        year = self.request.query_params.get("year") # type: ignore
        month = self.request.query_params.get("month") # type: ignore
        search = self.request.query_params.get("search") # type: ignore

        if year:
            queryset = queryset.filter(timestamp__year=year)

        if month:
            queryset = queryset.filter(timestamp__month=month)

        if search:
            queryset = queryset.filter(
                Q(reference_code__icontains=search)
                | Q(notes__icontains=search)
                | Q(member__first_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__email__icontains=search)
            )

        return queryset

    @action(detail=False, methods=["get"], url_path="trashed")
    def trashed(self, request):
        queryset = Tithe.all_objects.filter(
            assembly=request.user.church, # type: ignore
            is_trash=True,
        ).select_related("member", "assembly", "report")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="contributors")
    def contributors(self, request):
        now = timezone.now().date()
        year = int(request.query_params.get("year") or now.year)
        month = int(request.query_params.get("month") or now.month)
        queryset = self._filtered_active_queryset()

        grouped = (
            queryset
            .values(
                "member_id",
                "member__first_name",
                "member__middle_name",
                "member__last_name",
                "member__membership_status",
            )
            .annotate(
                this_month=Sum(
                    "amount",
                    filter=Q(timestamp__year=year, timestamp__month=month),
                    default=Decimal("0.00"),
                ),
                year_to_date=Sum(
                    "amount",
                    filter=Q(timestamp__year=year),
                    default=Decimal("0.00"),
                ),
                last_contribution=Max("timestamp"),
                average_contribution=Avg("amount"),
            )
            .order_by("member__last_name", "member__first_name", "member_id")
        )

        rows = []
        for row in grouped:
            name_parts = [
                row.get("member__first_name"),
                row.get("member__middle_name"),
                row.get("member__last_name"),
            ]
            contributor = " ".join(part for part in name_parts if part).strip()

            rows.append({
                "member_id": row["member_id"],
                "contributor": contributor or "Anonymous",
                "this_month": row["this_month"],
                "year_to_date": row["year_to_date"],
                "last_contribution": row["last_contribution"],
                "average_contribution": row["average_contribution"] or Decimal("0.00"),
                "receipt_preference": None,
                "status": row.get("member__membership_status"),
            })

        return Response({
            "count": len(rows),
            "results": rows,
        })

    @action(detail=False, methods=["get"], url_path="receipts")
    def receipts(self, request):
        queryset = self._filtered_active_queryset().filter(
            receipt__isnull=False,
        ).exclude(receipt="")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="performance")
    def performance(self, request):
        today = timezone.now().date()
        year = int(request.query_params.get("year") or today.year)
        month = int(request.query_params.get("month") or today.month)
        period_start = today.replace(year=year, month=month, day=1)
        last_day = calendar.monthrange(year, month)[1]
        period_end = period_start.replace(day=last_day)

        forecast = Forecast.objects.filter(
            assembly=request.user.church, # type: ignore
            year=year,
            month=month,
            status=Forecast.Status.ACTIVE,
        ).first()
        actual = self._filtered_active_queryset().filter(
            timestamp__gte=period_start,
            timestamp__lte=period_end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        if not forecast:
            return Response({
                "target": None,
                "actual": actual,
                "period": {"year": year, "month": month},
                "detail": "No tithe target has been set for this period.",
            })

        target = forecast.tithes_collected
        remaining = target - actual

        return Response({
            "target": target,
            "actual": actual,
            "remaining": remaining,
            "achievement": (actual / target) if target else None,
            "period": {"year": year, "month": month},
            "forecast_id": forecast.id,
        })

    @action(detail=False, methods=["get"], url_path="audit-log")
    def audit_log(self, request):
        tithe_ids = Tithe.all_objects.filter(
            assembly=request.user.church, # type: ignore
        ).values_list("id", flat=True)
        content_type = ContentType.objects.get_for_model(Tithe)
        queryset = AuditLog.objects.filter(
            content_type=content_type,
            object_id__in=tithe_ids,
        ).select_related("user", "content_type").order_by("-timestamp")

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(queryset, many=True)
        return Response(serializer.data)
