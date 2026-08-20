from dataclasses import dataclass
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.people.models import Member
from apps.people.models.assembly_membership import AssemblyMembershipStatus
from apps.people.permissions import filter_membership_queryset_for_user
from apps.reports.models import AssemblyReport

from .serializers import (
    MembershipSummaryArgumentsSerializer,
    PrepareTitheArgumentsSerializer,
    ReportStatusArgumentsSerializer,
    SearchMembersArgumentsSerializer,
)
from .tithe_services import prepare_tithe_creation


def _member_queryset(context):
    return filter_membership_queryset_for_user(
        Member.objects.filter(is_trash=False, assembly=context.active_assembly),
        context.user,
    )


def search_members(context, arguments, conversation=None):
    query = " ".join(arguments["query"].split())
    compact_query = "".join(query.split())
    queryset = _member_queryset(context).filter(
        Q(first_name__icontains=query)
        | Q(middle_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(member_key__icontains=compact_query)
    )
    if arguments.get("status"):
        queryset = queryset.filter(membership_status__iexact=arguments["status"])

    results = []
    for member in queryset.select_related("assembly")[: arguments["limit"]]:
        results.append({
            "public_id": member.member_key,
            "member_number": member.member_key,
            "full_name": member.full_name,
            "membership_status": member.membership_status,
            "gender": member.gender,
            "date_joined": member.membersince.isoformat() if member.membersince else None,
            "assembly_name": member.assembly.name if member.assembly else None,
        })
    return {"type": "members", "results": results, "count": len(results)}


def get_membership_summary(context, arguments, conversation=None):
    today = timezone.localdate()
    queryset = _member_queryset(context)
    period = arguments["period"]
    new_members = queryset
    if period == "current_month":
        new_members = new_members.filter(membersince__year=today.year, membersince__month=today.month)
    elif period == "current_year":
        new_members = new_members.filter(membersince__year=today.year)

    active_statuses = [AssemblyMembershipStatus.ACTIVE]
    data = {
        "total_members": queryset.count(),
        "active_members": queryset.filter(assembly_memberships__status__in=active_statuses).distinct().count(),
        "inactive_members": queryset.filter(assembly_memberships__status=AssemblyMembershipStatus.INACTIVE).distinct().count(),
        "new_members": new_members.count(),
        "male": queryset.filter(gender__iexact="Male").count(),
        "female": queryset.filter(gender__iexact="Female").count(),
    }
    return {"type": "summary", "period": period, "data": data}


def get_report_submission_status(context, arguments, conversation=None):
    year, month = (int(part) for part in arguments["period"].split("-"))
    report = (
        AssemblyReport.objects.filter(
            assembly=context.active_assembly,
            period_start__year=year,
            period_start__month=month,
        )
        .select_related("submitted_by")
        .first()
    )
    if report is None:
        return {
            "type": "report_status",
            "results": [],
            "missing_reports": ["Monthly assembly report"],
            "period": arguments["period"],
        }
    return {
        "type": "report_status",
        "results": [{
            "report_name": "Monthly assembly report",
            "period": arguments["period"],
            "status": report.status,
            "submitted_date": report.submitted_at.isoformat() if report.submitted_at else None,
            "submitted_by": report.submitted_by.full_name if report.submitted_by else None,
        }],
        "missing_reports": [],
        "period": arguments["period"],
    }


@dataclass(frozen=True)
class ToolDefinition:
    description: str
    serializer: type
    handler: object
    parameters: dict
    strict: bool = False

    def schema(self, name):
        return {
            "type": "function",
            "name": name,
            "description": self.description,
            "strict": self.strict,
            "parameters": self.parameters,
        }


TOOLS = {
    "prepare_tithe_creation": ToolDefinition(
        "Prepare, but never create, a tithe draft for confirmation. Use only after the user asks to record a tithe and all required details are known.",
        PrepareTitheArgumentsSerializer,
        prepare_tithe_creation,
        {
            "type": "object",
            "properties": {
                "member_query": {"type": "string"},
                "amount": {"type": "string", "pattern": "^[0-9]+(?:\\.[0-9]{1,2})?$"},
                "payment_method": {"type": "string"},
                "payment_date": {"type": ["string", "null"], "format": "date"},
                "reference": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["member_query", "amount", "payment_method", "payment_date", "reference", "notes"],
            "additionalProperties": False,
        },
        strict=True,
    ),
    "search_members": ToolDefinition(
        "Search members in the user's active, permitted assembly by name or member number.",
        SearchMembersArgumentsSerializer,
        search_members,
        {"type": "object", "properties": {"query": {"type": "string"}, "status": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}, "required": ["query"], "additionalProperties": False},
    ),
    "get_membership_summary": ToolDefinition(
        "Return reliable membership totals for the active assembly.",
        MembershipSummaryArgumentsSerializer,
        get_membership_summary,
        {"type": "object", "properties": {"period": {"type": "string", "enum": ["current_month", "current_year", "all_time"]}}, "required": ["period"], "additionalProperties": False},
    ),
    "get_report_submission_status": ToolDefinition(
        "Return monthly report submission status for the active assembly.",
        ReportStatusArgumentsSerializer,
        get_report_submission_status,
        {"type": "object", "properties": {"period": {"type": "string", "pattern": "^\\d{4}-(0[1-9]|1[0-2])$"}, "report_type": {"type": "string"}}, "required": ["period"], "additionalProperties": False},
    ),
}


def tool_schemas():
    return [definition.schema(name) for name, definition in TOOLS.items()]


def execute_tool(name, arguments, context, conversation=None):
    definition = TOOLS.get(name)
    if definition is None:
        raise ValidationError({"tool": "Unknown tool."})
    serializer = definition.serializer(data=arguments)
    serializer.is_valid(raise_exception=True)
    return definition.handler(context, serializer.validated_data, conversation)
