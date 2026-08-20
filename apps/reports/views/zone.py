import calendar
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.churches.models import Church
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import IntegerField, Sum, DecimalField
from django.db.models.functions import Coalesce
from apps.reports.models import AssemblyReport
from apps.reports.permissions import CanViewZoneReport

class ZoneReportView(APIView):
    permission_classes = [CanViewZoneReport]

    def get(self, request, zone_id):
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year:
            return Response({"error": "year is required"}, status=400)

        zone = getattr(request, "zone", None)

        if not zone:
            return Response({"error": "Zone not found"}, status=404)

        assemblies = Church.objects.filter(zone=zone)

        reports = AssemblyReport.objects.filter(
            assembly__in=assemblies,
            period_start__year=year,
            status=AssemblyReport.Status.DRAFT
        ).select_related("assembly").order_by("period_start")

        if month:
            reports = reports.filter(period_start__month=month)

        # -------------------------
        # ZONE SUMMARY
        # -------------------------
        summary = reports.aggregate(
            total_attendance=Coalesce(Sum("attendance_total"), 0, output_field=IntegerField()),
            total_adults=Coalesce(Sum("total_adults"), 0, output_field=IntegerField()),
            total_children=Coalesce(Sum("total_children"), 0, output_field=IntegerField()),
            total_visitors=Coalesce(Sum("total_visitors"), 0, output_field=IntegerField()),
            total_new_converts=Coalesce(Sum("total_new_converts"), 0, output_field=IntegerField()),
            total_altar_call=Coalesce(Sum("total_altar_call"), 0, output_field=IntegerField()),
            total_baptisms=Coalesce(Sum("total_baptisms"), 0, output_field=IntegerField()),
            total_members=Coalesce(Sum("members_total"), 0, output_field=IntegerField()),

            total_income=Coalesce(Sum("income_total"), 0, output_field=DecimalField(max_digits=20, decimal_places=2)),
            total_expenses=Coalesce(Sum("expense_total"), 0, output_field=DecimalField(max_digits=20, decimal_places=2)),
            total_balance=Coalesce(Sum("balance"), 0, output_field=DecimalField(max_digits=20, decimal_places=2)),
            total_tithes=Coalesce(Sum("tithe_total"), 0, output_field=DecimalField(max_digits=20, decimal_places=2)),
        )
        
        total_assemblies = assemblies.count()
        finalized_count = reports.values("assembly").distinct().count()

        compliance_rate = (
            (finalized_count / total_assemblies) * 100
            if total_assemblies else 0
        )

        grouped_data = defaultdict(list)

        for report in reports:
            month_number = report.period_start.month
            month_name = calendar.month_name[month_number].lower()

            tithe_ratio = (
                (report.tithe_total / report.income_total) * 100
                if report.income_total else 0
            )

            expense_ratio = (
                (report.expense_total / report.income_total) * 100
                if report.income_total else 0
            )

            per_capita_giving = (
                report.income_total / report.attendance_total
                if report.attendance_total else 0
            )

            grouped_data[month_name].append({
                "id": report.assembly.id,
                "name": report.assembly.name,

                "attendance": report.attendance_total,
                "total_adults": report.total_adults,
                "total_children": report.total_children,
                "total_visitors": report.total_visitors,
                "total_new_converts": report.total_new_converts,
                "total_altar_call": report.total_altar_call,
                "total_baptisms": report.total_baptisms,
                "income": report.income_total,
                "expenses": report.expense_total,
                "balance": report.balance,

                "tithe_ratio": round(tithe_ratio, 2),
                "expense_ratio": round(expense_ratio, 2),
                "per_capita_giving": round(per_capita_giving, 2),

                "members_total": report.members_total,
                "is_finalized": report.status == AssemblyReport.Status.SUBMITTED,
                "report_status": "On Time",
            })

        # -------------------------
        # FINAL RESPONSE
        # -------------------------

        return Response({
            "zone": {
                "id": zone.id,
                "name": zone.name
            },
            "period": {
                "year": int(year),
                "month": int(month) if month else None
            },
            "summary": {
                **summary,
                "compliance_rate": round(compliance_rate, 2)
            },
            "assemblies_by_month": grouped_data
        })
    

