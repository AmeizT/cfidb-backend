from django.db.models import Sum, Avg, F, ExpressionWrapper, IntegerField, DecimalField
from django.db.models.functions import TruncWeek
from django.db.models.functions import TruncMonth
from datetime import datetime, date
from django.utils import timezone

class OverviewAnalyticsService:
    def __init__(self, assembly, start_date, end_date):
        self.assembly = assembly
        self.start_date = self._to_aware_datetime(start_date)
        self.end_date = self._to_aware_datetime(end_date)

    def _to_aware_datetime(self, value):
        if value is None:
            return None

        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())

        if timezone.is_naive(value):
            return timezone.make_aware(value)

        return value

    def get_attendance_trend(self):
        from django.db.models import F, ExpressionWrapper, IntegerField
        from apps.people.models.attendance import Attendance
        from apps.people.models.sunday_school import SundaySchoolAttendance

        attendance_rows = (
            Attendance.objects
            .filter(
                assembly=self.assembly,
                timestamp__gte=self.start_date,
                timestamp__lte=self.end_date
            )
            .annotate(
                week=TruncWeek("timestamp"),
                headcount_calc=ExpressionWrapper(
                    F("total_adults")
                    + F("total_visitors")
                    + F("online_viewers"),
                    output_field=IntegerField()
                )
            )
            .values("week")
            .annotate(total=Sum("headcount_calc"))
            .order_by("week")
        )
        children_rows = (
            SundaySchoolAttendance.objects
            .filter(
                assembly=self.assembly,
                service_date__gte=self.start_date,
                service_date__lte=self.end_date,
                is_deleted=False,
            )
            .annotate(week=TruncWeek("service_date"))
            .values("week")
            .annotate(total=Sum(F("boys") + F("girls")))
        )

        totals_by_week = {
            row["week"]: row["total"] or 0
            for row in attendance_rows
        }

        for row in children_rows:
            week = row["week"]
            totals_by_week[week] = totals_by_week.get(week, 0) + (row["total"] or 0)

        return [
            {"week": week, "total": total}
            for week, total in sorted(totals_by_week.items())
        ]
    

    def get_kpis(self):
        from django.db.models import F, ExpressionWrapper, IntegerField, DecimalField
        from apps.people.models.attendance import Attendance
        from apps.people.models.sunday_school import SundaySchoolAttendance
        from apps.bookkeeper.models import Expenditure, Revenue
        from apps.bookkeeper.models import Tithe, Overhead

        # Attendance queryset
        attendance = Attendance.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).annotate(
            headcount_calc=ExpressionWrapper(
                F("total_adults")
                + F("total_visitors")
                + F("online_viewers"),
                output_field=IntegerField()
            )
        )
        children_total = (
            SundaySchoolAttendance.objects
            .filter(
                assembly=self.assembly,
                service_date__gte=self.start_date,
                service_date__lte=self.end_date,
                is_deleted=False,
            )
            .aggregate(total=Sum(F("boys") + F("girls")))["total"]
            or 0
        )

        # Expenditure queryset (compute amount if not stored)
        expenditure = Expenditure.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).annotate(
            computed_amount=ExpressionWrapper(
                F("price") * F("quantity"),
                output_field=DecimalField()
            )
        )

        # Revenue queryset (assumes amount exists)
        revenue = Revenue.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        )

        tithes_total = Tithe.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).aggregate(total=Sum("amount"))["total"] or 0

        overhead_total = Overhead.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        ).aggregate(total=Sum("amount"))["total"] or 0

        revenue_total = revenue.aggregate(total=Sum("amount"))["total"] or 0
        expense_total = expenditure.aggregate(total=Sum("computed_amount"))["total"] or 0

        net_revenue = revenue_total + tithes_total
        net_expenditure = expense_total + overhead_total

        # NOTE:
        # total_revenue = revenue only (excluding tithes)
        # total_expense = expenditure only (excluding overhead)
        # net_* values = combined totals (full financial picture)

        attendance_base_total = attendance.aggregate(total=Sum("headcount_calc"))["total"] or 0
        total_attendance = attendance_base_total + children_total
        attendance_records = attendance.count()
        avg_attendance = total_attendance / attendance_records if attendance_records else 0

        return {
            # Averages
            "avg_attendance": avg_attendance,

            # Totals
            "total_attendance": total_attendance,
            "total_revenue": revenue_total,
            "total_expense": expense_total,
            "total_tithes": tithes_total,
            "total_overhead": overhead_total,

            # Net (combined)
            "net_revenue": net_revenue,
            "net_expenditure": net_expenditure,
        }
    
    def get_finance_breakdown(self):
        from apps.bookkeeper.models import Tithe, Overhead

        tithes = Tithe.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        )

        overhead = Overhead.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        )

        tithes_total = tithes.aggregate(total=Sum("amount"))["total"] or 0
        overhead_total = overhead.aggregate(total=Sum("amount"))["total"] or 0

        return {
            "giving": {
                "tithes": tithes_total,
            },
            "expenses": {
                "overhead": overhead_total,
            }
        }

    def get_membership_trend(self):
        from apps.people.models import Member
        from django.db.models import Count

        return (
            Member.objects
            .filter(
                assembly=self.assembly,
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            )
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
    
    def generate(self):
        return {
            "kpis": self.get_kpis(),
            "attendance_trend": list(self.get_attendance_trend()),
            # "finance": self.get_finance_breakdown(),
            "membership_trend": list(self.get_membership_trend()),
        }
