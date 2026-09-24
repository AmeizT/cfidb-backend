from rest_framework import serializers
from apps.bookkeeper.serializers.overhead import OverheadSerializer
from apps.bookkeeper.serializers.revenue import RevenueSerializer
from apps.reports.models import AssemblyReport, AuditLog, ReportVersion
from django.contrib.contenttypes.models import ContentType
from apps.people.serializers import AttendanceSerializer
from apps.bookkeeper.serializers import FinanceSummarySerializer, FixedExpenditureSerializer, IncomeSerializer, TitheSerializer
from apps.core.serializers.base import HyperlinkedModelSerializer
from apps.reports.services.metrics.assembly_metrics import get_assembly_dashboard
from apps.churches.models.assembly import Church
from django.utils import timezone
from apps.reports.services.lifecycle import get_report_sections, get_report_state, validate_report


class AssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "name", "country", "currency", "zone"]


class AssemblyReportSerializer(HyperlinkedModelSerializer):
    app_name = "reports"   
    basename = "assembly_report"
    assembly = AssemblySerializer()

    status = serializers.SerializerMethodField()
    workflow_status = serializers.CharField(source="status", read_only=True)
    capabilities = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    findings = serializers.SerializerMethodField()
    due_at = serializers.SerializerMethodField()
    editable_until = serializers.SerializerMethodField()
    current_version = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    compliance = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta: # type: ignore
        model = AssemblyReport
        fields = [
            "id",
            "assembly",
            "period_start",
            "period_end",
            "status",
            "workflow_status",
            "submitted_at",
            "due_at",
            "editable_until",
            "current_version",
            "completion_percentage",
            "capabilities",
            "sections",
            "findings",
            "attendance_total",
            "total_adults",
            "total_children",
            "total_visitors",
            "total_new_converts",
            "total_altar_call",
            "total_baptisms",
            "total_online_viewers",
            "income_total",
            "expense_total",
            "tithe_total",
            "balance",
            "members_total",
            "compliance",
            "metrics",
        ]

    def get_metrics(self, obj):
        return get_assembly_dashboard(obj)

    def _state(self, obj):
        cache = getattr(self, "_state_cache", {})
        key = obj.pk or id(obj)
        if key not in cache:
            request = self.context.get("request")
            cache[key] = get_report_state(
                obj,
                getattr(request, "user", None),
                sections=self._section_items(obj),
            )
            self._state_cache = cache
        return cache[key]

    def _section_items(self, obj):
        cache = getattr(self, "_section_cache", {})
        key = obj.pk or id(obj)
        if key not in cache:
            cache[key] = get_report_sections(obj)
            self._section_cache = cache
        return cache[key]

    def get_status(self, obj):
        return self._state(obj).status

    def get_due_at(self, obj):
        return self._state(obj).due_at

    def get_editable_until(self, obj):
        return self._state(obj).editable_until

    def get_current_version(self, obj):
        return self._state(obj).current_version

    def get_completion_percentage(self, obj):
        return self._state(obj).completion_percentage

    def get_capabilities(self, obj):
        state = self._state(obj)
        return {
            "is_overdue": state.is_overdue,
            "is_locked": state.is_locked,
            "is_editable": state.is_editable,
            "backfill_active": state.backfill_active,
            "can_submit": state.can_submit,
            "can_amend": state.can_amend,
            "can_request_reopen": state.can_request_reopen,
            "can_approve_reopen": state.can_approve_reopen,
        }

    def get_sections(self, obj):
        return [
            {
                "id": item["object"].pk,
                "key": item["key"],
                "name": item["key"],
                "label": item["label"],
                "status": item["status"],
                "resolved": item["resolved"],
                "total": item["source"]["total"],
                "record_count": item["source"]["record_count"],
                "source": item["source"]["source"],
                "skip_reason_code": item["object"].skip_reason,
                "skip_reason_detail": item["object"].skip_notes,
                "skipped_by": item["object"].skipped_by_id,
                "skipped_at": item["object"].skipped_at,
                "no_activity_confirmed_by": item["object"].no_activity_confirmed_by_id,
                "no_activity_confirmed_at": item["object"].no_activity_confirmed_at,
                "no_activity_note": item["object"].no_activity_note,
            }
            for item in self._section_items(obj)
        ]

    def get_findings(self, obj):
        return validate_report(obj, self._section_items(obj))

    def get_compliance(self, obj):
        state = self._state(obj)
        sections = self.get_sections(obj)
        skipped = sum(1 for section in sections if section["status"] == "skipped")
        return {
            "total_sections": state.required_section_count,
            "completed": state.resolved_section_count - skipped,
            "skipped": skipped,
            "pending": state.required_section_count - state.resolved_section_count,
            "progress": state.completion_percentage,
            "coverage": state.completion_percentage,
            "status": "COMPLIANT" if state.resolved_section_count == state.required_section_count else "INCOMPLETE",
            "report_status": state.status,
            "sections": sections,
        }

    # def get_compliance(self, obj):
    #     return obj.get_compliance()
    

class UnifiedReportSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField() # type: ignore
    finance_summary = serializers.SerializerMethodField()

    class Meta:
        model = AssemblyReport
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "finalized_at"]

    def get_data(self, obj):
        return {
            "attendances": AttendanceSerializer(obj.attendance_set.all(), many=True).data,
            "tithes": TitheSerializer(obj.tithe_set.all(), many=True).data,
            "incomes": IncomeSerializer(obj.income_set.all(), many=True).data,
            "expenditures": FixedExpenditureSerializer(obj.expenditure_set.all(), many=True).data,
            "revenue": RevenueSerializer(obj.revenue_set.all(), many=True).data,
            "overhead": OverheadSerializer(obj.overhead_set.all(), many=True).data,
        }

    def get_finance_summary(self, obj):
        church = obj.church

        if not obj.period_start:
            return {}

        year = obj.period_start.year
        month = obj.period_start.month

        return FinanceSummarySerializer.get_data(church, year, month)

    def validate(self, data): # type: ignore
        if self.instance and self.instance.status == "finalized":
            raise serializers.ValidationError("Cannot edit a finalized report. Please ask admin to reopen.")
        return data
    

class ZoneReportAssemblySerializer(serializers.Serializer):
    assembly_id = serializers.IntegerField()
    assembly_name = serializers.CharField()

    attendance_total = serializers.IntegerField()
    income_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    expense_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    tithe_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)

    members_total = serializers.IntegerField()
    status = serializers.CharField()


class ReportVersionSummarySerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = ReportVersion
        fields = [
            "id", "version_number", "submitted_at", "submitted_by",
            "submitted_by_name", "editable_until", "is_locked",
        ]

    def get_submitted_by_name(self, obj):
        return obj.submitted_by.full_name if obj.submitted_by else None

    def get_is_locked(self, obj):
        return timezone.now() > obj.editable_until


class SubmittedReportSerializer(serializers.ModelSerializer):
    assembly = AssemblySerializer()
    status = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()
    version_history = serializers.SerializerMethodField()
    audit_history = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = ReportVersion
        fields = [
            "id", "report", "version_number", "status", "assembly",
            "period_start", "period_end", "submitted_by", "submitted_by_name",
            "submitted_at", "editable_until", "declaration_confirmed",
            "validation_findings", "attendance_total", "sunday_school_attendance_total",
            "tithe_total", "revenue_total", "operating_expense_total",
            "activity_other_expense_total", "net_balance", "sections",
            "version_history", "capabilities",
            "audit_history",
        ]

    assembly = serializers.SerializerMethodField()
    period_start = serializers.DateField(source="report.period_start")
    period_end = serializers.DateField(source="report.period_end")

    def get_assembly(self, obj):
        return AssemblySerializer(obj.report.assembly).data

    def get_status(self, obj):
        report = obj.report
        if report.current_version_id == obj.id and report.amendment_started_at:
            return "reopened"
        return "locked" if timezone.now() > obj.editable_until else "submitted"

    def get_submitted_by_name(self, obj):
        return obj.submitted_by.full_name if obj.submitted_by else None

    def get_sections(self, obj):
        return [
            {
                "id": section.id,
                "key": section.section,
                "label": section.label,
                "status": section.status,
                "total": section.total,
                "record_count": section.record_count,
                "breakdown": section.breakdown,
                "source": section.source_references,
                "skip_reason_code": section.skip_reason_code,
                "skip_reason_detail": section.skip_reason_detail,
                "skipped_by": section.skipped_by_id,
                "skipped_at": section.skipped_at,
                "no_activity_confirmed_by": section.no_activity_confirmed_by_id,
                "no_activity_confirmed_at": section.no_activity_confirmed_at,
                "no_activity_note": section.no_activity_note,
            }
            for section in obj.section_snapshots.all()
        ]

    def get_version_history(self, obj):
        return ReportVersionSummarySerializer(obj.report.versions.all(), many=True).data

    def get_audit_history(self, obj):
        content_type = ContentType.objects.get_for_model(obj.report)
        return [
            {
                "id": event.id,
                "actor": event.user.full_name if event.user else None,
                "action": event.action,
                "description": event.description,
                "timestamp": event.timestamp,
                "previous": event.old_data,
                "current": event.new_data,
            }
            for event in AuditLog.objects.filter(
                content_type=content_type,
                object_id=obj.report_id,
            ).select_related("user").order_by("-timestamp")[:50]
        ]

    def get_capabilities(self, obj):
        request = self.context.get("request")
        state = get_report_state(obj.report, getattr(request, "user", None))
        return {
            "can_amend": state.can_amend,
            "can_request_reopen": state.can_request_reopen,
            "can_approve_reopen": state.can_approve_reopen,
            "is_locked": state.is_locked,
        }
