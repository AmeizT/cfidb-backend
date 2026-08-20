from datetime import timedelta
from django.db.models import Sum, Avg, F, ExpressionWrapper, IntegerField
from django.utils import timezone
from apps.people.models import Attendance

class HighlightEngine:
    def __init__(self, assembly, start_date, end_date):
        self.assembly = assembly
        self.start_date = start_date
        self.end_date = end_date

        self.previous_start, self.previous_end = self._get_previous_period()

        self.current_data = self._aggregate(self.start_date, self.end_date)
        self.previous_data = self._aggregate(self.previous_start, self.previous_end)
        self.series = self._get_time_series()
    def _get_time_series(self):
        from django.db.models.functions import TruncWeek
        from apps.people.models import SundaySchoolAttendance

        attendance_rows = (
            Attendance.objects
            .filter(
                assembly=self.assembly,
                timestamp__gte=self.start_date,
                timestamp__lte=self.end_date
            )
            .annotate(week=TruncWeek("timestamp"))
            .values("week")
            .annotate(
                total=ExpressionWrapper(
                    Sum("total_adults") + Sum("total_visitors") + Sum("online_viewers"),
                    output_field=IntegerField()
                )
            )
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

        return {
            "attendance": [
                {"week": week, "total": total}
                for week, total in sorted(totals_by_week.items())
            ]
        }

    # 🔁 Previous period (same duration)
    def _get_previous_period(self):
        delta = self.end_date - self.start_date
        previous_end = self.start_date - timedelta(days=1)
        previous_start = previous_end - delta
        return previous_start, previous_end

    # 📊 Aggregate core metrics
    def _aggregate(self, start, end):
        # Local import to avoid circular dependencies
        from apps.bookkeeper.models import Tithe, Revenue, Overhead, Expenditure
        from apps.people.models import SundaySchoolAttendance

        attendance_qs = Attendance.objects.filter(
            assembly=self.assembly,
            timestamp__gte=start,
            timestamp__lte=end,
        )
        attendance_qs = attendance_qs.annotate(
            headcount_calc=ExpressionWrapper(
                F("total_adults")
                + F("total_visitors")
                + F("online_viewers")
                + F("total_leaders_present")
                + F("volunteers_on_duty"),
                output_field=IntegerField()
            )
        )

        tithe_qs = Tithe.objects.filter(
            assembly=self.assembly,
            timestamp__range=[start, end],
        )

        revenue_qs = Revenue.objects.filter(
            assembly=self.assembly,
            timestamp__range=[start, end],
        )

        overhead_qs = Overhead.objects.filter(
            assembly=self.assembly,
            timestamp__range=[start, end],
        )

        expenditure_qs = Expenditure.objects.filter(
            assembly=self.assembly,
            timestamp__range=[start, end],
        )

        total_attendance = attendance_qs.aggregate(
            total=Sum("headcount_calc")
        )["total"] or 0
        children_total = (
            SundaySchoolAttendance.objects
            .filter(
                assembly=self.assembly,
                service_date__gte=start,
                service_date__lte=end,
                is_deleted=False,
            )
            .aggregate(total=Sum(F("boys") + F("girls")))["total"]
            or 0
        )
        total_attendance += children_total

        attendance_records = attendance_qs.count()
        avg_attendance = total_attendance / attendance_records if attendance_records else 0

        total_income = (
            (tithe_qs.aggregate(total=Sum("amount"))["total"] or 0) +
            (revenue_qs.aggregate(total=Sum("amount"))["total"] or 0)
        )

        total_expense = (
            (overhead_qs.aggregate(total=Sum("amount"))["total"] or 0) +
            (expenditure_qs.annotate(
                computed_amount=F("price") * F("quantity")
            ).aggregate(total=Sum("computed_amount"))["total"] or 0)
        )

        return {
            "attendance": total_attendance,
            "avg_attendance": avg_attendance,
            "net_revenue": total_income,
            "net_expenditure": total_expense,
        }

    # 📈 Percentage change
    def _percent_change(self, current, previous):
        if not previous:
            return None
        return ((current - previous) / previous) * 100

    # 🧠 Build structured insight
    def _build_insight(self, metric, change, current, previous, message, insight_type="info"):
        severity = 0

        if change is not None:
            severity = abs(change)

        # boost critical signals
        if insight_type == "danger":
            severity += 50
        elif insight_type == "warning":
            severity += 20

        suggestion = None

        # Simple AI-like suggestions
        if metric == "attendance" and change is not None and change < -10:
            suggestion = "Consider follow-ups, outreach, or midweek engagement."
        elif metric in ["income", "net_revenue"] and change is not None and change < -15:
            suggestion = "Encourage giving campaigns or stewardship teaching."
        elif metric == "expense" and self.current_data["net_expenditure"] > self.current_data["net_revenue"]:
            suggestion = "Review spending controls and approvals."

        return {
            "type": insight_type,
            "metric": metric,
            "change_percent": round(change, 2) if change is not None else None,
            "current": current,
            "previous": previous,
            "message": message,
            "severity": round(severity, 2),
            "suggestion": suggestion
        }

    # 🔍 ATTENDANCE INSIGHTS
    def attendance_growth(self):
        change = self._percent_change(
            self.current_data["attendance"],
            self.previous_data["attendance"],
        )

        if change is None:
            return None

        return self._build_insight(
            metric="attendance",
            change=change,
            current=self.current_data["attendance"],
            previous=self.previous_data["attendance"],
            message=f"Attendance changed by {round(change)}%",
            insight_type="success" if change > 0 else "warning"
        )

    # 💰 INCOME INSIGHTS
    def income_growth(self):
        change = self._percent_change(
            self.current_data["net_revenue"],
            self.previous_data["net_revenue"],
        )

        if change is None:
            return None

        return self._build_insight(
            metric="income",
            change=change,
            current=self.current_data["net_revenue"],
            previous=self.previous_data["net_revenue"],
            message=f"Giving changed by {round(change)}%",
            insight_type="success" if change > 0 else "warning"
        )

    def tithe_growth(self):
        from apps.bookkeeper.models import Tithe

        current = Tithe.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date,
        ).aggregate(total=Sum("amount"))["total"] or 0

        previous = Tithe.objects.filter(
            assembly=self.assembly,
            timestamp__gte=self.previous_start,
            timestamp__lte=self.previous_end,
        ).aggregate(total=Sum("amount"))["total"] or 0

        change = self._percent_change(current, previous)

        if change is None:
            return None

        return self._build_insight(
            metric="tithes",
            change=change,
            current=current,
            previous=previous,
            message=f"Tithes changed by {round(change)}%",
            insight_type="success" if change > 0 else "warning"
        )

    def membership_growth(self):
        from apps.people.models import Member
        from django.db.models import Count

        current = Member.objects.filter(
            assembly=self.assembly,
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
        ).aggregate(total=Count("id"))["total"] or 0

        previous = Member.objects.filter(
            assembly=self.assembly,
            created_at__gte=self.previous_start,
            created_at__lte=self.previous_end,
        ).aggregate(total=Count("id"))["total"] or 0

        change = self._percent_change(current, previous)

        if change is None:
            return None

        return self._build_insight(
            metric="membership",
            change=change,
            current=current,
            previous=previous,
            message=f"Membership grew by {round(change)}%",
            insight_type="success" if change > 0 else "warning"
        )

    def giving_vs_attendance(self):
        attendance = self.current_data["attendance"]
        revenue = self.current_data["net_revenue"]

        if attendance <= 0:
            return None

        giving_per_person = revenue / attendance

        # simple threshold (can be dynamic later)
        threshold = 50

        if giving_per_person < threshold:
            return self._build_insight(
                metric="giving_efficiency",
                change=None,
                current=round(giving_per_person, 2),
                previous=None,
                message=f"Giving per attendee is low ({round(giving_per_person,2)})",
                insight_type="warning"
            )

    def anomaly_attendance_drop(self):
        data = [x["total"] or 0 for x in self.series["attendance"]]

        if len(data) < 3:
            return None

        avg = sum(data[:-1]) / (len(data) - 1)
        latest = data[-1]

        if latest < avg * 0.7:
            return self._build_insight(
                metric="attendance_anomaly",
                change=None,
                current=latest,
                previous=round(avg),
                message="Attendance is significantly below normal trend",
                insight_type="danger"
            )


    def declining_attendance_trend(self):
        data = [x["total"] or 0 for x in self.series["attendance"]]

        if len(data) >= 3 and data[-1] < data[-2] < data[-3]:
            return self._build_insight(
                metric="attendance_trend",
                change=None,
                current=data[-1],
                previous=data[-3],
                message="Attendance has declined for 3 consecutive weeks",
                insight_type="warning"
            )


    def attendance_projection(self):
        data = [x["total"] or 0 for x in self.series["attendance"]]

        if len(data) < 2:
            return None

        trend = data[-1] - data[-2]

        if trend < 0:
            return self._build_insight(
                metric="attendance_projection",
                change=None,
                current=data[-1],
                previous=data[-2],
                message="Attendance may continue declining if trend persists",
                insight_type="warning"
            )

    # ⚠ EXPENSE WARNING
    def expense_warning(self):
        if self.current_data["net_expenditure"] > self.current_data["net_revenue"]:
            return self._build_insight(
                metric="expense",
                change=None,
                current=self.current_data["net_expenditure"],
                previous=self.current_data["net_revenue"],
                message="Expenses exceeded income in this period",
                insight_type="danger"
            )

    # 🔥 PEAK ATTENDANCE
    def peak_attendance(self):
        # Local import to avoid circular dependencies
        from apps.people.models import Attendance
        from apps.people.services import get_children_counts_by_date

        candidates = (
            Attendance.objects.filter(
                assembly=self.assembly,
                service_type="sunday",
                timestamp__gte=self.start_date,
                timestamp__lte=self.end_date,
            )
            .annotate(
                headcount_calc=ExpressionWrapper(
                    F("total_adults")
                    + F("total_visitors")
                    + F("online_viewers"),
                    output_field=IntegerField()
                )
            )
        )
        children_by_date = get_children_counts_by_date(
            self.assembly,
            self.start_date,
            self.end_date,
        )
        peak = None
        peak_total = 0

        for attendance in candidates:
            total = attendance.headcount_calc + children_by_date.get(attendance.timestamp, 0) # type: ignore
            if not peak or total > peak_total:
                peak = attendance
                peak_total = total

        if peak:
            return self._build_insight(
                metric="attendance_peak",
                change=None,
                current=peak_total,
                previous=None,
                message=f"Highest attendance was {peak_total} on {peak.timestamp.strftime('%d %b %Y')}",
                insight_type="info"
            )

    # 📉 LOW BALANCE WARNING
    def low_balance(self):
        net = self.current_data["net_revenue"] - self.current_data["net_expenditure"]

        if net < 0:
            return self._build_insight(
                metric="balance",
                change=None,
                current=net,
                previous=0,
                message=f"Net balance is negative ({net})",
                insight_type="danger"
            )

    # 🚀 MAIN ENTRY
    def generate(self):
        highlights = []

        checks = [
            self.anomaly_attendance_drop,
            self.declining_attendance_trend,
            self.attendance_projection,

            self.attendance_growth,
            self.membership_growth,
            self.income_growth,
            self.tithe_growth,
            self.giving_vs_attendance,

            self.expense_warning,
            self.peak_attendance,
            self.low_balance,
        ]

        for check in checks:
            result = check()
            if result:
                highlights.append(result)

        # Sort by severity (descending)
        highlights.sort(key=lambda x: x["severity"], reverse=True)

        # Return top 3 most important insights
        return highlights[:3]
