from calendar import month_name, monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db.models import Avg, Min, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework import permissions, status as http_status
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.bookkeeper.models import Tithe
from apps.bookkeeper.serializers import FinanceSummarySerializer, IncomeSerializer, TitheSerializer, ReportExpenseSerializer, ReportOverheadSerializer, RevenueSerializer
from apps.churches.models import Forecast
from apps.people.models import Member
from apps.people.services import get_children_counts_by_date, get_monthly_summary
from apps.reports.models import AssemblyReport, AuditLog, ReportReopeningRequest
from apps.reports.schemas import (
    get_attendance_schema,
    get_cashflow_schema,
    get_reports_table_schema,
    get_tithes_audit_schema,
    get_tithes_contributor_history_schema,
    get_tithes_contributors_schema,
    get_tithes_cumulative_schema,
    get_tithes_performance_schema,
    get_tithes_receipts_schema,
    get_tithes_schema,
)
from apps.bookkeeper.serializers import SimpleFinanceSerializer, normalize_cashflow
from apps.reports.serializers import AssemblyReportSerializer, AssemblySerializer, AuditLogSerializer, SubmittedReportSerializer
from apps.shared.pagination import DataTablePagination
from apps.reports.mixins import HighlightsMixin
from apps.reports.mixins.overview_analytics import OverviewAnalyticsMixin
from apps.reports.mixins.quarter_reports import ReportSummaryMixin
from apps.reports.services.tithe_contributors_pdf import (
    build_tithe_contributor_history_pdf,
    build_tithe_contributors_pdf,
    tithe_contributor_history_pdf_filename,
    tithe_contributors_pdf_filename,
)
from apps.reports.services.analytics.tithes_engine import build_tithes_year
from apps.reports.services.lifecycle import (
    ensure_report,
    get_due_at,
    get_report_sections,
    get_report_state,
    request_reopening,
    review_reopening,
    set_section_status,
    start_amendment,
    submit_report,
    validate_report,
)

class ReportViewSet(
    HighlightsMixin, 
    OverviewAnalyticsMixin, 
    ReportSummaryMixin, 
    ModelViewSet
):
    serializer_class = AssemblyReportSerializer
    pagination_class = DataTablePagination
    permission_classes = [permissions.IsAuthenticated]

    def _add_paginated_table_fields(self, response, rows, **extra):
        response.data["data"] = rows

        for key, value in extra.items():
            response.data[key] = value

        return response

    def _with_meta_config(self, **extra):
        config = extra.get("config")
        meta = dict(extra.get("meta") or {})

        if config is not None and "config" not in meta:
            meta["config"] = config

        if config is not None and "table_schema" not in extra:
            extra["table_schema"] = config

        if meta:
            extra["meta"] = meta

        return extra

    def _get_tithe_field_names(self):
        return {field.name for field in Tithe._meta.fields}

    def _get_deleted_filter(self, deleted):
        field_names = self._get_tithe_field_names()

        if "is_deleted" in field_names:
            return Q(is_deleted=deleted)

        if "is_trash" in field_names:
            return Q(is_trash=deleted)

        return Q(pk__isnull=True) if deleted else Q()

    def _get_voided_filter(self):
        field_names = self._get_tithe_field_names()

        if "status" in field_names:
            return Q(status="VOIDED")

        if "is_voided" in field_names:
            return Q(is_voided=True)

        return Q(pk__isnull=True)

    def _parse_tithe_period(self, request, report):
        today = timezone.localdate()
        period = request.query_params.get("period")
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if period:
            if period.startswith("year:"):
                year = period.split(":", 1)[1]

            if period.startswith("month:"):
                _, value = period.split(":", 1)
                parts = value.split("-", 1)
                if len(parts) == 2:
                    year, month = parts

        try:
            parsed_year = int(year) if year else report.period_start.year
        except (TypeError, ValueError):
            parsed_year = today.year

        try:
            parsed_month = int(month) if month else None
        except (TypeError, ValueError):
            parsed_month = None

        if parsed_month is not None and not 1 <= parsed_month <= 12:
            parsed_month = None

        return parsed_year, parsed_month

    def _get_tithe_reports_for_period(self, request, report):
        year, month = self._parse_tithe_period(request, report)
        queryset = AssemblyReport.objects.filter(
            assembly=report.assembly,
            period_start__year=year,
        )

        if month:
            queryset = queryset.filter(period_start__month=month)

        return queryset

    def _get_report_tithe_queryset(self, report, *, include_deleted=False):
        manager = Tithe.all_objects if include_deleted and hasattr(Tithe, "all_objects") else Tithe.objects

        return manager.filter(report=report).select_related(
            "member",
            "assembly",
            "report",
        )

    def _filter_report_tithes(self, request, report, queryset, *, apply_status=True):
        year, month = self._parse_tithe_period(request, report)
        search = request.query_params.get("search")
        ordering = request.query_params.get("ordering") or request.query_params.get("sort")

        if request.query_params.get("year") or request.query_params.get("period"):
            queryset = queryset.filter(timestamp__year=year)

        if month:
            queryset = queryset.filter(timestamp__month=month)

        if apply_status:
            status_filter = request.query_params.get("status", "active")
            deleted_filter = self._get_deleted_filter(True)
            active_filter = self._get_deleted_filter(False)
            voided_filter = self._get_voided_filter()

            if status_filter == "deleted":
                queryset = queryset.filter(deleted_filter)
            elif status_filter == "voided":
                queryset = queryset.filter(active_filter).filter(voided_filter)
            else:
                queryset = queryset.filter(active_filter).exclude(voided_filter)

        if search:
            queryset = queryset.filter(
                Q(reference_code__icontains=search)
                | Q(notes__icontains=search)
                | Q(member__first_name__icontains=search)
                | Q(member__middle_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__email__icontains=search)
            )

        if ordering:
            allowed_ordering = {
                "timestamp",
                "-timestamp",
                "created_at",
                "-created_at",
                "amount",
                "-amount",
            }
            requested = [
                field for field in ordering.split(",")
                if field in allowed_ordering
            ]

            if requested:
                return queryset.order_by(*requested)

        return queryset

    def _serialize_tithe_row(self, tithe):
        data = TitheSerializer(tithe).data
        member = tithe.member

        data.update({
            "member_name": member.full_name if member else None,
            "member_avatar": member.avatar.url if member and member.avatar else None,
            "member_avatar_fallback": member.avatar_fallback if member else None,
        })

        return data

    def _paginated_tithe_response(self, queryset, **extra):
        extra = self._with_meta_config(**extra)
        page = self.paginate_queryset(queryset)

        if page is not None:
            paginated_rows = [self._serialize_tithe_row(tithe) for tithe in page]
            response = self.get_paginated_response(paginated_rows)
            return self._add_paginated_table_fields(response, paginated_rows, **extra)

        rows = [self._serialize_tithe_row(tithe) for tithe in queryset]

        return Response({
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "results": rows,
            "data": rows,
            **extra,
        })

    def _decimal(self, value):
        if value is None:
            return Decimal("0.00")

        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _median_decimal(self, values):
        amounts = sorted(self._decimal(value) for value in values if value is not None)

        if not amounts:
            return Decimal("0.00")

        midpoint = len(amounts) // 2

        if len(amounts) % 2:
            return amounts[midpoint]

        return self._decimal((amounts[midpoint - 1] + amounts[midpoint]) / 2)

    def _ordinal(self, value):
        day = int(value)

        if 10 <= day % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return f"{day}{suffix}"

    def _get_tithe_interval(self, dates, paid_months):
        if not dates:
            return None

        ordered_dates = sorted(dates)

        if len(ordered_dates) >= 36:
            return "Weekly"

        if len(ordered_dates) > 1:
            gaps = [
                (ordered_dates[index] - ordered_dates[index - 1]).days
                for index in range(1, len(ordered_dates))
            ]
            average_gap = sum(gaps) / len(gaps)

            if average_gap <= 10:
                return "Weekly"

            if 25 <= average_gap <= 40:
                return "Monthly"

        if len(paid_months) >= 9:
            return "Monthly"

        return "Irregular"

    def _get_average_payment_date(self, dates, interval):
        if not dates:
            return None

        if interval == "Weekly":
            weekdays = {}

            for value in dates:
                weekdays[value.weekday()] = weekdays.get(value.weekday(), 0) + 1

            weekday = max(weekdays, key=weekdays.get)
            return f"{['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][weekday]} of each week"

        average_day = round(sum(value.day for value in dates) / len(dates))

        if interval == "Monthly":
            return f"{self._ordinal(average_day)} of each month"

        return f"{self._ordinal(average_day)} average day"

    def _get_tithe_receipt_value(self, tithe):
        if not tithe.receipt:
            return None

        try:
            return tithe.receipt.url
        except ValueError:
            return tithe.receipt.name or None

    def _get_tithe_recorded_by(self, tithe):
        created_by = getattr(tithe, "created_by", None)

        if created_by:
            return getattr(created_by, "full_name", None) or str(created_by)

        return None

    def _empty_tithe_history_row(self, year, month_number, row_id_prefix):
        return {
            "id": f"{row_id_prefix}-{year}-{month_number:02d}",
            "month": month_name[month_number],
            "month_number": month_number,
            "amount": Decimal("0.00"),
            "payment_method": None,
            "recorded_by": None,
            "recorded_date": None,
            "receipt": None,
        }

    def _serialize_tithe_history(self, tithes, year, row_id_prefix):
        history = {
            month_number: self._empty_tithe_history_row(year, month_number, row_id_prefix)
            for month_number in range(1, 13)
        }

        for tithe in tithes:
            month_number = tithe.timestamp.month
            recorded_date = tithe.created_at.date().isoformat() if tithe.created_at else None
            current = history[month_number]

            history[month_number] = {
                "id": f"{row_id_prefix}-{year}-{month_number:02d}",
                "month": month_name[month_number],
                "month_number": month_number,
                "amount": self._decimal(current["amount"] + tithe.amount),
                "payment_method": tithe.payment_method,
                "recorded_by": self._get_tithe_recorded_by(tithe),
                "recorded_date": recorded_date,
                "receipt": self._get_tithe_receipt_value(tithe),
            }

        return [history[month_number] for month_number in range(1, 13)]

    def get_queryset(self): # type: ignore
        user = self.request.user
        queryset = AssemblyReport.objects.select_related("assembly")

        # 1️⃣ Admins and DB staff see everything
        if user.is_admin or user.is_db_staff: # type: ignore
            pass

        # 2️⃣ Zone staff see only churches in their zones
        elif user.is_db_zone_staff: # type: ignore
            assembly_ids = user.assemblies.values_list("id", flat=True) # type: ignore
            queryset = queryset.filter(assembly_id__in=assembly_ids)

        # 3️⃣ All other users → MUST have active church
        else:
            if not user.church_id: # type: ignore
                raise PermissionDenied("No active church selected.")

            queryset = queryset.filter(assembly_id=user.church_id) # type: ignore

        year = self.request.query_params.get("year") # type: ignore
        month = self.request.query_params.get("month") # type: ignore

        if year:
            queryset = queryset.filter(period_start__year=int(year))
        if month:
            queryset = queryset.filter(period_start__month=int(month))

        return queryset.order_by("period_start")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)

            return self._add_paginated_table_fields(
                response,
                serializer.data,
                table_schema=get_reports_table_schema(),
            )

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "count": len(serializer.data),
            "next": None,
            "previous": None,
            "results": serializer.data,
            "data": serializer.data,
            "table_schema": get_reports_table_schema(),
        })

    def _active_assembly(self, request):
        if not getattr(request.user, "church_id", None):
            raise PermissionDenied("No active assembly selected.")
        return request.user.church

    def _period_from_request(self, request):
        today = timezone.localdate()
        try:
            year = int(request.query_params.get("year") or today.year)
            month = int(request.query_params.get("month") or today.month)
            return date(year, month, 1), date(year, month, monthrange(year, month)[1])
        except (TypeError, ValueError):
            raise DRFValidationError({"period": "Use a valid year and month."})

    def _placeholder_period(self, assembly, start, end):
        due_report = AssemblyReport(assembly=assembly, period_start=start, period_end=end)
        due_at = get_due_at(due_report)
        today = timezone.localdate()
        applicable = assembly.status == "open" and (
            not assembly.established_date or end >= assembly.established_date
        )
        return {
            "id": None,
            "assembly": AssemblySerializer(assembly).data,
            "period_start": start,
            "period_end": end,
            "status": "not_required" if not applicable else (
                "overdue" if timezone.now() > due_at else "not_started"
            ),
            "workflow_status": None,
            "submitted_at": None,
            "due_at": due_at,
            "editable_until": None,
            "current_version": None,
            "completion_percentage": 0,
            "capabilities": {
                "is_overdue": applicable and timezone.now() > due_at,
                "is_locked": False,
                "is_editable": applicable and start <= today.replace(day=1),
                "can_start": applicable and start <= today.replace(day=1),
                "can_submit": False,
                "can_amend": False,
                "can_request_reopen": False,
                "can_approve_reopen": False,
            },
            "sections": [
                {
                    "id": None,
                    "key": key,
                    "name": key,
                    "label": label,
                    "status": "not_started",
                    "resolved": False,
                    "total": 0,
                    "record_count": 0,
                }
                for key, label in __import__(
                    "apps.reports.models", fromlist=["ReportSectionStatus"]
                ).ReportSectionStatus.Section.choices
            ],
            "findings": [],
        }

    @action(detail=False, methods=["get"])
    def overview(self, request):
        assembly = self._active_assembly(request)
        try:
            year = int(request.query_params.get("year") or timezone.localdate().year)
        except (TypeError, ValueError):
            raise DRFValidationError({"year": "Use a valid year."})
        reports = {
            report.period_start.month: report
            for report in self.get_queryset().filter(period_start__year=year).prefetch_related(
                "sections", "versions", "current_version__section_snapshots"
            )
        }
        months = []
        for month in range(1, 13):
            start = date(year, month, 1)
            end = date(year, month, monthrange(year, month)[1])
            report = reports.get(month)
            months.append(
                self.get_serializer(report).data if report else self._placeholder_period(assembly, start, end)
            )

        current_versions = [report.current_version for report in reports.values() if report.current_version_id]
        submitted = {
            "general_attendance": sum(version.attendance_total for version in current_versions),
            "sunday_school_attendance": sum(version.sunday_school_attendance_total for version in current_versions),
            "tithes": sum((version.tithe_total for version in current_versions), Decimal("0")),
            "revenue": sum((version.revenue_total for version in current_versions), Decimal("0")),
            "operating_expenses": sum((version.operating_expense_total for version in current_versions), Decimal("0")),
            "activity_other_expenses": sum((version.activity_other_expense_total for version in current_versions), Decimal("0")),
        }
        provisional = {
            "general_attendance": 0,
            "sunday_school_attendance": 0,
            "tithes": Decimal("0"),
            "revenue": Decimal("0"),
            "operating_expenses": Decimal("0"),
            "activity_other_expenses": Decimal("0"),
        }
        for report in reports.values():
            if report.current_version_id and not report.amendment_started_at:
                continue
            for section in get_report_sections(report):
                provisional[section["key"]] += section["source"]["total"]
        return Response({
            "assembly": {"id": assembly.id, "name": assembly.name, "currency": assembly.currency},
            "year": year,
            "months": months,
            "cumulative": {"submitted": submitted, "provisional": provisional},
        })

    @action(detail=False, methods=["get"])
    def activity(self, request):
        queryset = self.get_queryset().prefetch_related("sections", "versions", "current_version")
        requested_status = request.query_params.get("status")
        rows = list(queryset)
        if requested_status:
            statuses = {value.strip() for value in requested_status.split(",") if value.strip()}
            rows = [row for row in rows if get_report_state(row, request.user).status in statuses]
        serializer = self.get_serializer(rows, many=True)
        return Response({"count": len(rows), "next": None, "previous": None, "results": serializer.data})

    @action(detail=False, methods=["get", "post"])
    def current(self, request):
        assembly = self._active_assembly(request)
        start, end = self._period_from_request(request)
        report = AssemblyReport.objects.filter(
            assembly=assembly, period_start=start, period_end=end
        ).prefetch_related("sections", "versions").select_related("current_version").first()
        if request.method == "POST":
            if start > timezone.localdate().replace(day=1):
                raise DRFValidationError({"period": "Future reporting periods cannot be started."})
            report = ensure_report(
                assembly=assembly, period_start=start, period_end=end, actor=request.user
            )
        if report is None:
            return Response(self._placeholder_period(assembly, start, end))
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["get", "post"], url_path=r"sections/(?P<section_key>[^/.]+)")
    def section(self, request, pk=None, section_key=None):
        report = self.get_object()
        if request.method == "POST":
            set_section_status(
                report=report,
                section_key=section_key,
                status=request.data.get("status"),
                actor=request.user,
                skip_reason_code=request.data.get("skip_reason_code"),
                skip_reason_detail=request.data.get("skip_reason_detail"),
                no_activity_note=request.data.get("no_activity_note"),
            )
            report.refresh_from_db()
        item = next((item for item in get_report_sections(report) if item["key"] == section_key), None)
        if item is None:
            raise DRFValidationError({"section": "Unknown report section."})
        payload = next(
            section for section in self.get_serializer(report).data["sections"]
            if section["key"] == section_key
        )
        payload["breakdown"] = item["source"]["breakdown"]
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="validate")
    def validate_lifecycle(self, request, pk=None):
        report = self.get_object()
        findings = validate_report(report)
        state = get_report_state(report, request.user)
        return Response({
            "eligible": state.can_submit,
            "findings": findings,
            "status": state.status,
        })

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        report = self.get_object()
        version = submit_report(
            report=report,
            actor=request.user,
            declaration_confirmed=request.data.get("declaration_confirmed") is True,
        )
        return Response(
            SubmittedReportSerializer(version, context={"request": request}).data,
            status=http_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def amend(self, request, pk=None):
        report = start_amendment(
            report=self.get_object(), actor=request.user, reason=request.data.get("reason", "")
        )
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"], url_path="request-reopening")
    def request_reopening_action(self, request, pk=None):
        reopening = request_reopening(
            report=self.get_object(), actor=request.user, reason=request.data.get("reason", "")
        )
        return Response({"id": reopening.id, "status": reopening.status}, status=http_status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="review-reopening")
    def review_reopening_action(self, request, pk=None):
        report = self.get_object()
        reopening = report.reopening_requests.filter(
            pk=request.data.get("request_id"), status=ReportReopeningRequest.Status.REQUESTED
        ).first()
        if not reopening:
            raise DRFValidationError({"request_id": "Active reopening request not found."})
        reopening = review_reopening(
            request_obj=reopening,
            actor=request.user,
            approve=request.data.get("decision") == "approve",
            decision_note=request.data.get("decision_note", ""),
        )
        return Response({"id": reopening.id, "status": reopening.status})

    @action(detail=True, methods=["get"])
    def submitted(self, request, pk=None):
        report = self.get_object()
        version_number = request.query_params.get("version")
        versions = report.versions.select_related("submitted_by", "report__assembly").prefetch_related(
            "section_snapshots", "report__versions"
        )
        version = versions.filter(version_number=version_number).first() if version_number else report.current_version
        if version is None:
            raise DRFValidationError({"report": "This report has not been submitted."})
        return Response(SubmittedReportSerializer(version, context={"request": request}).data)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"submitted/sections/(?P<section_key>[^/.]+)",
    )
    def submitted_section(self, request, pk=None, section_key=None):
        report = self.get_object()
        version_number = request.query_params.get("version")
        version = report.versions.filter(version_number=version_number).first() if version_number else report.current_version
        if version is None:
            raise DRFValidationError({"report": "This report has not been submitted."})
        section = version.section_snapshots.filter(section=section_key).first()
        if section is None:
            raise DRFValidationError({"section": "Submitted section not found."})
        full = SubmittedReportSerializer(version, context={"request": request}).data
        return Response(next(item for item in full["sections"] if item["key"] == section_key))

    @action(detail=True)
    def attendance(self, request, pk=None):
        report = self.get_object()

        # Compute monthly summary
        first_attendance = report.attendance_set.first()
        monthly_summary = None
        if first_attendance:
            monthly_summary = get_monthly_summary(
                assembly=first_attendance.assembly,
                year=first_attendance.timestamp.year,
                month=first_attendance.timestamp.month,
            )

        queryset = report.attendance_set.all()
        totals = queryset.aggregate(
            total_adults=Sum("total_adults"),
            total_visitors=Sum("total_visitors"),
            total_new_converts=Sum("total_new_converts"),
            total_altar_call=Sum("total_altar_call"),
            total_baptisms=Sum("total_baptisms"),
        )
        children_by_date = get_children_counts_by_date(
            report.assembly,
            report.period_start,
            report.period_end,
        )
        total_children = sum(children_by_date.values())
        attendance_auto_sum = (
            (totals["total_adults"] or 0) +
            total_children +
            (totals["total_visitors"] or 0)
        )
        page = self.paginate_queryset(queryset)
        page_queryset = page if page is not None else queryset
        data = []

        for a in page_queryset:
            children = children_by_date.get(a.timestamp, 0)
            data.append({
                "id": a.id,
                "timestamp": a.timestamp,
                "service_type": a.service_type,
                "is_special_event": a.is_special_event,
                "special_event_name": a.special_event_name,
                "preacher": a.preacher,
                "total_adults": a.total_adults,
                "total_children": children,
                "total_visitors": a.total_visitors,
                "online_viewers": a.online_viewers,
                "headcount": a.total_adults + children + a.total_visitors + a.online_viewers,
                "total_new_converts": a.total_new_converts,
                "total_altar_call": a.total_altar_call,
                "total_baptisms": a.total_baptisms,
                "total_leaders_present": a.total_leaders_present,
                "weather": a.weather,
                "notes": a.notes,
                "sermon": a.sermon,
                "scriptures": a.scriptures,
                "is_deleted": a.is_deleted,
                "legacy": {
                    "adults": a.adults,
                    "guest_attendance": a.guest_attendance,
                    "new_converts": a.new_converts,
                    "altar_call": a.altar_call,
                    "baptisms": a.baptisms,
                },
            })

        extra = {
            "config": get_attendance_schema(request.user),
            "meta": {
                "attendance_auto_sum": attendance_auto_sum,
                "breakdown": {
                    "total_adults": totals["total_adults"] or 0,
                    "total_children": total_children,
                    "total_visitors": totals["total_visitors"] or 0,
                    "total_new_converts": totals["total_new_converts"] or 0,
                    "total_altar_call": totals["total_altar_call"] or 0,
                    "total_baptisms": totals["total_baptisms"] or 0,
                }
            }
        }

        if page is not None:
            response = self.get_paginated_response(data)
            return self._add_paginated_table_fields(response, data, **extra)

        return Response({
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "results": data,
            "data": data,
            **extra,
        })

    

    @action(detail=True)
    def tithes(self, request, pk=None):
        report = self.get_object()
        queryset = self._get_report_tithe_queryset(
            report,
            include_deleted=True,
        )
        queryset = self._filter_report_tithes(request, report, queryset)
        total_tithes = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        extra = {
            "config": get_tithes_schema(request.user),
            "meta": {
                "tithes_auto_sum": total_tithes,
            }
        }

        return self._paginated_tithe_response(queryset, **extra)

    def _get_tithe_contributors_payload(self, request, report):
        year, selected_month = self._parse_tithe_period(request, report)
        selected_month = selected_month or report.period_start.month
        reports = AssemblyReport.objects.filter(
            assembly=report.assembly,
            period_start__year=year,
        )
        queryset = Tithe.all_objects.filter(
            report__in=reports,
            timestamp__year=year,
            member__isnull=False,
        ).select_related("member", "assembly", "report")
        queryset = queryset.filter(self._get_deleted_filter(False)).exclude(
            self._get_voided_filter()
        )

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(reference_code__icontains=search)
                | Q(notes__icontains=search)
                | Q(member__first_name__icontains=search)
                | Q(member__middle_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__email__icontains=search)
            )

        contributor_groups = {}

        for tithe in queryset.order_by(
            "member__last_name",
            "member__first_name",
            "member_id",
            "timestamp",
            "created_at",
        ):
            member = tithe.member
            group_key = f"member:{tithe.member_id}" if tithe.member_id else "anonymous"

            if group_key not in contributor_groups:
                contributor_groups[group_key] = {
                    "member_id": tithe.member_id,
                    "member": member,
                    "tithes": [],
                }

            contributor_groups[group_key]["tithes"].append(tithe)

        rows = []

        for group_key, group in contributor_groups.items():
            member = group["member"]
            tithes = group["tithes"]
            row_id_prefix = group_key.replace(":", "-")
            history = self._serialize_tithe_history(tithes, year, row_id_prefix)
            payment_amounts = [
                self._decimal(history_row["amount"])
                for history_row in history
                if self._decimal(history_row["amount"]) > Decimal("0.00")
            ]
            dates = [tithe.timestamp for tithe in tithes]
            paid_months = {tithe.timestamp.month for tithe in tithes if tithe.amount > 0}
            cumulative = self._decimal(sum(payment_amounts, Decimal("0.00")))
            interval = self._get_tithe_interval(dates, paid_months)
            average_contribution = (
                self._decimal(cumulative / len(payment_amounts))
                if payment_amounts
                else Decimal("0.00")
            )
            commitment = (
                (Decimal(len(paid_months)) / Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if paid_months
                else Decimal("0.00")
            )

            rows.append({
                "member_id": group["member_id"],
                "contributor": member.full_name if member else "Anonymous",
                "contributor_avatar": member.avatar.url if member and member.avatar else None,
                "contributor_avatar_fallback": member.avatar_fallback if member else None,
                "cumulative": cumulative,
                "median": self._median_decimal(payment_amounts),
                "interval": interval,
                "average_payment_date": self._get_average_payment_date(dates, interval),
                "commitment": commitment,
                "status": member.membership_status if member else None,
                "history": history,
                "this_month": history[selected_month - 1]["amount"],
                "year_to_date": cumulative,
                "first_contribution": min(dates) if dates else None,
                "last_contribution": max(dates) if dates else None,
                "average_contribution": average_contribution,
                "receipt_preference": None,
            })

        rows = sorted(rows, key=lambda row: (row["contributor"].lower(), row["member_id"] or 0))
        contributor_count = len(rows)
        cumulative_tithes = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        average_contribution = queryset.aggregate(average=Avg("amount"))["average"] or Decimal("0.00")
        new_contributors = (
            queryset
            .values("member_id")
            .annotate(first_contribution=Min("timestamp"))
            .filter(first_contribution__year=year, first_contribution__month=selected_month)
            .count()
        )

        meta = {
            "total_contributors": contributor_count,
            "cumulative_tithes": cumulative_tithes,
            "average_contribution": average_contribution,
            "median_contribution": self._median_decimal([row["median"] for row in rows]),
            "new_contributors": new_contributors,
            "period": {"year": year, "month": selected_month},
            "config": get_tithes_contributors_schema(request.user),
        }

        return rows, meta, year, selected_month

    @action(detail=True, methods=["get"], url_path="tithes/contributors")
    def tithe_contributors(self, request, pk=None):
        report = self.get_object()
        rows, meta, _year, _selected_month = self._get_tithe_contributors_payload(request, report)
        contributor_count = len(rows)

        page = self.paginate_queryset(rows)

        if page is not None:
            paginated_rows = list(page)
            response = self.get_paginated_response(paginated_rows)
            response.data["data"] = paginated_rows
            response.data["meta"] = meta
            response.data["table_schema"] = meta["config"]
            return response
        
        return Response({
            "count": contributor_count,
            "next": None,
            "previous": None,
            "results": rows,
            "data": rows,
            "table_schema": meta["config"],
            "meta": meta,
        })

    @action(detail=True, methods=["get"], url_path=r"tithes/contributors/export\.pdf")
    def tithe_contributors_export_pdf(self, request, pk=None):
        if not (
            request.user.is_admin
            or request.user.is_staff
            or getattr(request.user, "is_db_staff", False)
            or getattr(request.user, "is_region_staff", False)
        ):
            raise PermissionDenied("You do not have permission to export contributor reports.")

        report = self.get_object()
        rows, _meta, year, selected_month = self._get_tithe_contributors_payload(request, report)
        pdf_buffer = build_tithe_contributors_pdf(
            report=report,
            rows=rows,
            year=year,
            month=selected_month,
        )

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=tithe_contributors_pdf_filename(report, year, selected_month),
            content_type="application/pdf",
        )

    def _get_tithe_contributor_history_export_payload(self, request, report, member_id):
        year, selected_month = self._parse_tithe_period(request, report)
        reports = AssemblyReport.objects.filter(
            assembly=report.assembly,
            period_start__year=year,
        )

        if selected_month:
            reports = reports.filter(period_start__month=selected_month)

        is_anonymous = str(member_id).lower() in {"anonymous", "null", "none"}
        member_filter = Q(member__isnull=True) if is_anonymous else Q(member_id=member_id)
        queryset = Tithe.all_objects.filter(
            report__in=reports,
            timestamp__year=year,
        ).select_related("member", "assembly", "report")

        if selected_month:
            queryset = queryset.filter(timestamp__month=selected_month)

        queryset = queryset.filter(member_filter)
        queryset = queryset.filter(self._get_deleted_filter(False)).exclude(
            self._get_voided_filter()
        ).order_by("timestamp", "created_at")

        records = list(queryset)
        member = records[0].member if records and records[0].member else None

        if not member and not is_anonymous:
            member = Member.objects.filter(pk=member_id, assembly=report.assembly).first()

        contributor_name = "Anonymous"
        if member:
            contributor_name = member.full_name
        elif not is_anonymous:
            contributor_name = f"Contributor {member_id}"

        total = sum((tithe.amount for tithe in records), Decimal("0.00"))

        return {
            "records": records,
            "contributor_name": contributor_name,
            "total": total,
            "year": year,
            "month": selected_month,
        }

    @action(detail=True, methods=["get"], url_path=r"tithes/contributors/(?P<member_id>[^/.]+)/history/pdf")
    def tithe_contributor_history_pdf(self, request, pk=None, member_id=None):
        report = self.get_object()
        payload = self._get_tithe_contributor_history_export_payload(request, report, member_id)
        pdf_buffer = build_tithe_contributor_history_pdf(
            report=report,
            contributor_name=payload["contributor_name"],
            records=payload["records"],
            total=payload["total"],
            year=payload["year"],
            month=payload["month"],
        )

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=tithe_contributor_history_pdf_filename(
                payload["contributor_name"],
                payload["year"],
                payload["month"],
            ),
            content_type="application/pdf",
        )

    @action(detail=True, methods=["get"], url_path=r"tithes/contributors/(?P<member_id>[^/.]+)/history")
    def tithe_contributor_history(self, request, pk=None, member_id=None):
        report = self.get_object()
        year, _month = self._parse_tithe_period(request, report)
        reports = AssemblyReport.objects.filter(
            assembly=report.assembly,
            period_start__year=year,
        )
        member_filter = (
            Q(member__isnull=True)
            if str(member_id).lower() in {"anonymous", "null", "none"}
            else Q(member_id=member_id)
        )
        queryset = Tithe.all_objects.filter(
            report__in=reports,
            timestamp__year=year,
        ).select_related("member", "assembly", "report")
        queryset = queryset.filter(member_filter)
        queryset = queryset.filter(self._get_deleted_filter(False)).exclude(
            self._get_voided_filter()
        ).order_by("timestamp", "created_at")
        rows = self._serialize_tithe_history(
            list(queryset),
            year,
            f"member-{member_id}",
        )
        meta = {
            "member_id": member_id,
            "period": {"year": year},
            "config": get_tithes_contributor_history_schema(request.user),
        }

        page = self.paginate_queryset(rows)

        if page is not None:
            paginated_rows = list(page)
            response = self.get_paginated_response(paginated_rows)
            response.data["data"] = paginated_rows
            response.data["meta"] = meta
            response.data["table_schema"] = meta["config"]
            return response

        return Response({
            "count": len(rows),
            "next": None,
            "previous": None,
            "results": rows,
            "data": rows,
            "table_schema": meta["config"],
            "meta": meta,
        })

    @action(detail=True, methods=["get"], url_path="tithes/analytics")
    def tithe_analytics(self, request, pk=None):
        report = self.get_object()
        year, _month = self._parse_tithe_period(request, report)
        payload = build_tithes_year(report.assembly, year)
        statements = payload.get("data", {}).get("statements", [])
        meta = payload.setdefault("meta", {})
        meta["config"] = get_tithes_cumulative_schema(request.user)

        return Response({
            "count": len(statements),
            "next": None,
            "previous": None,
            "results": statements,
            "table_schema": meta["config"],
            **payload,
        })

    @action(detail=True, methods=["get"], url_path="tithes/performance")
    def tithe_performance(self, request, pk=None):
        report = self.get_object()
        year, month = self._parse_tithe_period(request, report)
        month = month or report.period_start.month
        period_start = report.period_start.replace(year=year, month=month, day=1)
        period_end = period_start.replace(day=monthrange(year, month)[1])

        queryset = Tithe.all_objects.filter(
            assembly=report.assembly,
            timestamp__gte=period_start,
            timestamp__lte=period_end,
        ).filter(self._get_deleted_filter(False)).exclude(self._get_voided_filter())
        actual = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        forecast = Forecast.objects.filter(
            assembly=report.assembly,
            year=year,
            month=month,
            status=Forecast.Status.ACTIVE,
        ).first()

        if not forecast:
            row = {
                "target": None,
                "actual": actual,
                "remaining": None,
                "achievement": None,
                "period": {"year": year, "month": month},
                "detail": "No tithe target has been set for this period.",
            }

            return Response({
                "count": 1,
                "next": None,
                "previous": None,
                "results": [row],
                "data": row,
                **row,
                "table_schema": get_tithes_performance_schema(request.user),
                "meta": {
                    "period": {"year": year, "month": month},
                    "config": get_tithes_performance_schema(request.user),
                },
            })

        target = forecast.tithes_collected
        row = {
            "target": target,
            "actual": actual,
            "remaining": target - actual,
            "achievement": (actual / target) if target else None,
            "period": {"year": year, "month": month},
            "forecast_id": forecast.id,
        }

        return Response({
            "count": 1,
            "next": None,
            "previous": None,
            "results": [row],
            "data": row,
            **row,
            "table_schema": get_tithes_performance_schema(request.user),
            "meta": {
                "period": {"year": year, "month": month},
                "config": get_tithes_performance_schema(request.user),
            },
        })

    @action(detail=True, methods=["get"], url_path="tithes/receipts")
    def tithe_receipts(self, request, pk=None):
        report = self.get_object()
        queryset = self._get_report_tithe_queryset(report)
        queryset = self._filter_report_tithes(
            request,
            report,
            queryset,
            apply_status=False,
        )
        queryset = queryset.filter(self._get_deleted_filter(False)).exclude(
            self._get_voided_filter()
        ).filter(receipt__isnull=False).exclude(receipt="")

        return self._paginated_tithe_response(
            queryset,
            config=get_tithes_receipts_schema(request.user),
            meta={
                "receipt_count": queryset.count(),
            },
        )

    @action(detail=True, methods=["get"], url_path="tithes/audit-log")
    def tithe_audit_log(self, request, pk=None):
        report = self.get_object()
        tithe_ids = Tithe.all_objects.filter(report=report).values_list("id", flat=True)
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
                | Q(action__icontains=search)
            )

        meta = {
            "config": get_tithes_audit_schema(request.user),
        }
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["data"] = serializer.data
            response.data["meta"] = meta
            response.data["table_schema"] = meta["config"]
            return response

        serializer = AuditLogSerializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "results": serializer.data,
            "data": serializer.data,
            "table_schema": meta["config"],
            "meta": meta,
        })

    @action(detail=True)
    def income(self, request, pk=None):
        report = self.get_object()
        serializer = IncomeSerializer(report.income_set.all(), many=True)
        return Response(serializer.data)

    @action(detail=True)
    def expenses(self, request, pk=None):
        report = self.get_object()
        serializer = ReportExpenseSerializer(report)
        return Response(serializer.data)
    
    @action(detail=True)
    def overheads(self, request, pk=None):
        report = self.get_object()
        serializer = ReportOverheadSerializer(report)
        return Response(serializer.data)

    @action(detail=True)
    def revenue(self, request, pk=None):
        report = self.get_object()
        serializer = RevenueSerializer(report.revenue_set.all(), many=True)
        return Response(serializer.data)

    @action(detail=True)
    def cashflow_summary(self, request, pk=None):
        report = self.get_object()

        cache_key = f"report_cashflow_{report.id}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        data = FinanceSummarySerializer.from_report(report)

        cache.set(cache_key, data, timeout=60*5)
        return Response(data)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        report = self.get_object()
        version = submit_report(
            report=report,
            actor=request.user,
            declaration_confirmed=request.data.get("declaration_confirmed", True),
        )

        cache.delete(f"report_cashflow_{report.id}")
        cache.delete(f"report_summary_{report.id}")

        return Response({"status": "submitted", "version": version.version_number})

    @action(detail=True)
    def cashflow(self, request, pk=None):
        report = self.get_object()
        
        raw_data = SimpleFinanceSerializer.from_report(report)
        rows = normalize_cashflow(raw_data)

        data = {
            "rows": rows,
            "totals": raw_data["totals"]
        }

        page = self.paginate_queryset(rows)

        if page is not None:
            paginated_data = {
                "rows": page,
                "totals": raw_data["totals"],
            }
            response = self.get_paginated_response(page)
            response.data["data"] = paginated_data
            response.data["config"] = get_cashflow_schema(request.user)

            return response

        return Response({
            "count": len(rows),
            "next": None,
            "previous": None,
            "results": rows,
            "data": data,
            "config": get_cashflow_schema(request.user),
        })


    @action(detail=True, methods=["get"])
    def compliance(self, request, pk=None):
        report = self.get_object()
        return Response(report.get_compliance())
