import calendar
from datetime import date
from collections import defaultdict
from django.db.models import Count
from apps.bookkeeper.models import FixedExpenditure, Tithe, Income, Expenditure  # assuming these apps
from apps.people.models import Attendance

def analyze_assembly_data(assembly, year, upto_month=None):
    if hasattr(assembly, 'is_active') and not assembly.is_active:
        return None
    today = date.today()
    current_month = upto_month or (today.month if today.year == year else 12)

    results = []
    # For summary statistics
    missing_tithes = 0
    missing_income = 0
    missing_expenditure = 0
    missing_attendance = 0
    total_completion = 0
    total_stars = 0
    n_months = current_month
    for month in range(1, current_month + 1):
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        # Tithes (>= 2 per month)
        tithes_count = Tithe.objects.filter(
            assembly=assembly, timestamp__range=(start_date, end_date), is_trash=False
        ).count()
        tithes_ok = tithes_count >= 2
        tithes_comment = "OK" if tithes_ok else f"Only {tithes_count} record(s) (need 2+)"
        if not tithes_ok:
            missing_tithes += 1

        # Income (>= 1 per month)
        income_ok = Income.objects.filter(
            church=assembly, timestamp__range=(start_date, end_date)
        ).exists()
        income_comment = "OK" if income_ok else "Missing"
        if not income_ok:
            missing_income += 1

        # Expenditure (>= 1 per month)
        expenditure_ok = FixedExpenditure.objects.filter(
            assembly=assembly, timestamp__range=(start_date, end_date)
        ).exists()
        expenditure_comment = "OK" if expenditure_ok else "Missing"
        if not expenditure_ok:
            missing_expenditure += 1

        # Attendance (weekly, compare weeks in month)
        weeks_in_month = len(calendar.Calendar().monthdatescalendar(year, month))
        attendance_count = Attendance.objects.filter(
            church=assembly, timestamp__range=(start_date, end_date)
        ).count()
        attendance_ok = attendance_count >= weeks_in_month
        attendance_comment = (
            "OK" if attendance_ok else f"{attendance_count}/{weeks_in_month} weeks"
        )
        if not attendance_ok:
            missing_attendance += 1

        # Completion percentage (4 categories)
        completed = sum([tithes_ok, income_ok, expenditure_ok, attendance_ok])
        completion_percentage = round(100 * completed / 4)
        total_completion += completion_percentage

        # Star score (5 stars if all, else deduct 1 per missing)
        stars = 5 - (4 - completed)
        if stars < 1:
            stars = 1
        total_stars += stars

        # Overdue: current date > 5th of next month and incomplete
        overdue = False
        if today > end_date.replace(day=1) and today > end_date.replace(day=1).replace(month=month % 12 + 1, year=year if month < 12 else year + 1):
            overdue_date = end_date.replace(day=1).replace(month=month % 12 + 1, year=year if month < 12 else year + 1)
            overdue_date = overdue_date.replace(day=5)
            if today > overdue_date and completed < 4:
                overdue = True
        else:
            # Fallback: check if today > 5th of next month
            next_month = month % 12 + 1
            next_month_year = year if month < 12 else year + 1
            overdue_date = date(next_month_year, next_month, 5)
            if today > overdue_date and completed < 4:
                overdue = True

        results.append({
            "month": calendar.month_name[month],
            "tithes": tithes_ok,
            "income": income_ok,
            "expenditure": expenditure_ok,
            "attendance": attendance_ok,
            "tithes_comment": tithes_comment,
            "income_comment": income_comment,
            "expenditure_comment": expenditure_comment,
            "attendance_comment": attendance_comment,
            "completion_percentage": completion_percentage,
            "stars": stars,
            "overdue": overdue,
        })

    # Summary
    summary = {
        "missing_tithes": missing_tithes,
        "missing_income": missing_income,
        "missing_expenditure": missing_expenditure,
        "missing_attendance": missing_attendance,
        "average_completion_percentage": round(total_completion / n_months, 2) if n_months else 0,
        "average_stars": round(total_stars / n_months, 2) if n_months else 0,
    }
    return {
        "assembly": assembly.id,
        "assembly_name": assembly.name,
        "year": year,
        "data": results,
        "summary": summary,
    }




# Bulk analysis for multiple assemblies
def analyze_multiple_assemblies(assemblies, year, upto_month=None):
    """
    Efficiently analyze many assemblies for a given year and upto_month.
    Returns a list of dicts, each corresponding to the output of analyze_assembly_data.
    """
    # Filter out inactive assemblies
    assemblies = [a for a in assemblies if getattr(a, 'is_active', True)]
    today = date.today()
    current_month = upto_month or (today.month if today.year == year else 12)
    assemblies = list(assemblies)
    assembly_ids = [a.id for a in assemblies]
    assembly_id_to_obj = {a.id: a for a in assemblies}
    # Prepare all months
    months = list(range(1, current_month + 1))

    # Precompute month date ranges
    month_ranges = {}
    for month in months:
        start_date = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        month_ranges[month] = (start_date, end_date)

    # Bulk query Tithes (count per assembly per month)
    tithes_qs = (
        Tithe.objects.filter(
            assembly_id__in=assembly_ids,
            timestamp__year=year,
            is_trash=False
        )
        .values("assembly_id", "timestamp__month")
        .annotate(count=Count("id"))
    )
    tithes_counts = defaultdict(lambda: defaultdict(int))
    for row in tithes_qs:
        tithes_counts[row["assembly_id"]][row["timestamp__month"]] = row["count"]

    # Bulk query Income (exists per assembly per month)
    income_qs = (
        Income.objects.filter(
            church_id__in=assembly_ids,
            timestamp__year=year
        )
        .values("church_id", "timestamp__month")
        .annotate(count=Count("id"))
    )
    income_exists = defaultdict(set)
    for row in income_qs:
        income_exists[row["church_id"]].add(row["timestamp__month"])

    # Bulk query Expenditure (exists per assembly per month)
    expenditure_qs = (
        FixedExpenditure.objects.filter(
            assembly_id__in=assembly_ids,
            timestamp__year=year
        )
        .values("assembly_id", "timestamp__month")
        .annotate(count=Count("id"))
    )
    expenditure_exists = defaultdict(set)
    for row in expenditure_qs:
        expenditure_exists[row["assembly_id"]].add(row["timestamp__month"])

    # Bulk query Attendance (count per assembly per month)
    attendance_qs = (
        Attendance.objects.filter(
            church_id__in=assembly_ids,
            timestamp__year=year
        )
        .values("church_id", "timestamp__month")
        .annotate(count=Count("id"))
    )
    attendance_counts = defaultdict(lambda: defaultdict(int))
    for row in attendance_qs:
        attendance_counts[row["church_id"]][row["timestamp__month"]] = row["count"]

    results = []
    for assembly in assemblies:
        per_month_results = []
        missing_tithes = 0
        missing_income = 0
        missing_expenditure = 0
        missing_attendance = 0
        total_completion = 0
        total_stars = 0
        n_months = current_month
        for month in months:
            start_date, end_date = month_ranges[month]

            # Tithes (>=2 per month)
            tithes_count = tithes_counts[assembly.id].get(month, 0)
            tithes_ok = tithes_count >= 2
            tithes_comment = "OK" if tithes_ok else f"Only {tithes_count} record(s) (need 2+)"
            if not tithes_ok:
                missing_tithes += 1

            # Income (>=1 per month)
            income_ok = month in income_exists[assembly.id]
            income_comment = "OK" if income_ok else "Missing"
            if not income_ok:
                missing_income += 1

            # Expenditure (>=1 per month)
            expenditure_ok = month in expenditure_exists[assembly.id]
            expenditure_comment = "OK" if expenditure_ok else "Missing"
            if not expenditure_ok:
                missing_expenditure += 1

            # Attendance (weekly, compare to weeks in month)
            weeks_in_month = len(calendar.Calendar().monthdatescalendar(year, month))
            attendance_count = attendance_counts[assembly.id].get(month, 0)
            attendance_ok = attendance_count >= weeks_in_month
            attendance_comment = (
                "OK" if attendance_ok else f"{attendance_count}/{weeks_in_month} weeks"
            )
            if not attendance_ok:
                missing_attendance += 1

            completed = sum([tithes_ok, income_ok, expenditure_ok, attendance_ok])
            completion_percentage = round(100 * completed / 4)
            total_completion += completion_percentage

            stars = 5 - (4 - completed)
            if stars < 1:
                stars = 1
            total_stars += stars

            # Overdue logic (same as single)
            overdue = False
            if today > end_date.replace(day=1) and today > end_date.replace(day=1).replace(month=month % 12 + 1, year=year if month < 12 else year + 1):
                overdue_date = end_date.replace(day=1).replace(month=month % 12 + 1, year=year if month < 12 else year + 1)
                overdue_date = overdue_date.replace(day=5)
                if today > overdue_date and completed < 4:
                    overdue = True
            else:
                next_month = month % 12 + 1
                next_month_year = year if month < 12 else year + 1
                overdue_date = date(next_month_year, next_month, 5)
                if today > overdue_date and completed < 4:
                    overdue = True

            per_month_results.append({
                "month": calendar.month_name[month],
                "tithes": tithes_ok,
                "income": income_ok,
                "expenditure": expenditure_ok,
                "attendance": attendance_ok,
                "tithes_comment": tithes_comment,
                "income_comment": income_comment,
                "expenditure_comment": expenditure_comment,
                "attendance_comment": attendance_comment,
                "completion_percentage": completion_percentage,
                "stars": stars,
                "overdue": overdue,
            })

        summary = {
            "missing_tithes": missing_tithes,
            "missing_income": missing_income,
            "missing_expenditure": missing_expenditure,
            "missing_attendance": missing_attendance,
            "average_completion_percentage": round(total_completion / n_months, 2) if n_months else 0,
            "average_stars": round(total_stars / n_months, 2) if n_months else 0,
        }
        results.append({
            "assembly": assembly.id,
            "assembly_name": getattr(assembly, "name", str(assembly)),
            "year": year,
            "data": per_month_results,
            "summary": summary,
        })
    return results