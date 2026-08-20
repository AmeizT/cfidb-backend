from calendar import month_name
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField


def get_year_total(queryset, year, date_field="timestamp"):
    if queryset is None:
        return 0
    return queryset.filter(**{f"{date_field}__year": year}).aggregate(total=Sum("amount"))["total"] or 0


def forecast_next(current_total, change):
    if change is None:
        return None
    return current_total * (1 + change)


def calculate_percentage_change(current, previous):
    if not previous:
        return None
    return (current - previous) / previous


def get_previous_quarter(year: int, quarter: int):
    if quarter == 1:
        return year - 1, 4
    return year, quarter - 1


QUARTER_MAP = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}


def get_quarter_date_range(year: int, quarter: int):
    months = QUARTER_MAP[quarter]

    start = f"{year}-{months[0]:02d}-01"

    end_day = {
        3: "31",
        6: "30",
        9: "30",
        12: "31"
    }[months[-1]]

    end = f"{year}-{months[-1]:02d}-{end_day}"

    return start, end


def get_year_date_range(year: int):
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    return start, end


def build_analytics_statements(
    *,
    queryset=None,
    reports=None,
    year: int,
    period_type: str,  # "quarter" | "year"
    quarter: int = None,  # type: ignore
    value_fields=None,
    target: float = None, # type: ignore
    extra_aggregations=None,
    custom_row_builder=None,
    date_field: str = "timestamp",
    mode=None,
):
    """
    Generic analytics engine for quarter and year views
    """

    value_fields = value_fields or {}
    extra_aggregations = extra_aggregations or {}

    if period_type == "quarter":
        months = QUARTER_MAP.get(quarter)
        if not months:
            raise ValueError("Invalid quarter")
    elif period_type == "year":
        months = list(range(1, 13))
    else:
        raise ValueError("Invalid period_type")

    # Map report_id for drill-down
    report_map = {
        r.period_start.month: r.id
        for r in reports # type: ignore
    }

    # Build annotations
    annotations = {
        key: Sum(field)
        for key, field in value_fields.items()
    }
    # Ensure unified primary metric
    if "total" not in annotations and value_fields:
        first_field = next(iter(value_fields.values()))
        annotations["total"] = Sum(first_field)
    annotations.update(extra_aggregations)

    # ======================================
    # DATA SOURCE HANDLING (QUERYSET vs REPORTS)
    # ======================================
    if mode != "finance" and queryset is not None:
        monthly = (
            queryset
            .values(f"{date_field}__month")
            .annotate(**annotations)
        )

        data_map = {
            item[f"{date_field}__month"]: item
            for item in monthly
        }
    elif mode == "finance":
        # Finance mode: derive from reports directly
        data_map = {}

        for r in reports: # type: ignore
            month = r.period_start.month

            revenue = r.revenue_set.aggregate(total=Sum("amount"))["total"] or 0
            tithes = r.tithe_set.aggregate(total=Sum("amount"))["total"] or 0
            overhead = r.overhead_set.aggregate(total=Sum("amount"))["total"] or 0
            variable = r.variable_expenditure_set.aggregate(
                total=Sum(
                    ExpressionWrapper(F("price") * F("quantity"), output_field=DecimalField())
                )
            )["total"] or 0

            data_map[month] = {
                "total": revenue + tithes,
                "value": revenue + tithes,
                "metric": revenue + tithes,

                "expense_total": overhead + variable,
                "balance": (revenue + tithes) - (overhead + variable),
                "total": revenue + tithes - (overhead + variable),  # primary metric for analytics
            }
    else:
        data_map = {}

    statements = []

    for m in months:
        item = data_map.get(m)

        base = {
            "month": m,
            "label": month_name[m],
            "report_id": report_map.get(m),
            "is_missing": item is None,
        }

        if item:
            # Always include primary metric
            base["total"] = item.get("total", 0)

            # Optional domain-specific fields
            for key in ["givers", "revenue_total", "expense_total", "balance"]:
                if key in item:
                    base[key] = item.get(key, 0)
        else:
            # Default structure when missing
            base["total"] = 0
            base["value"] = 0
            base["metric"] = 0
            base["givers"] = 0
            base["expense_total"] = 0
            base["balance"] = 0

        for key in ["total", "value", "metric", "expense_total", "balance"]:
            base.setdefault(key, item.get(key, 0) if item else 0)

        base["balance"] = base.get("balance", 0) or (base.get("total", 0) - base.get("expense_total", 0))

        if custom_row_builder:
            base = custom_row_builder(base, item)

        if "total" in base and "givers" in base:
            givers = base.get("givers") or 0
            base["average"] = base["total"] / givers if givers else 0

        statements.append(base)

    # =========================
    # QUARTER KPIs
    # =========================
    valid = [s for s in statements if not s["is_missing"]]

    quarter_total = sum((s.get("total") or s.get("value") or s.get("metric") or 0) for s in valid)
    quarter_givers = sum(s.get("givers", 0) for s in valid)

    quarter_kpis = {
        "total": quarter_total,
        "givers": quarter_givers,
        "average": quarter_total / quarter_givers if quarter_givers else 0,
        "missing": len([s for s in statements if s["is_missing"]])
    }

    prev_year = None
    prev_quarter = None
    previous_total = None
    current_total = None
    change = None
    trend = "stable"

    start, end = (
        get_quarter_date_range(year, quarter) if period_type == "quarter"
        else get_year_date_range(year)
    )

    # =========================
    # QUARTER OVER QUARTER METRICS (GENERIC)
    # =========================
    if period_type == "quarter":
        prev_year, prev_quarter = get_previous_quarter(year, quarter)
        prev_months = QUARTER_MAP.get(prev_quarter, [])

        main_field = next(iter(value_fields.values()), "total")

        if queryset is not None:
            prev_total = (
                queryset.filter(**{f"{date_field}__month__in": prev_months})
                .aggregate(total=Sum(main_field))
                .get("total") or 0
            )

            current_total = (
                queryset.filter(**{f"{date_field}__month__in": months})
                .aggregate(total=Sum(main_field))
                .get("total") or 0
            )

            previous_total = prev_total
            change = calculate_percentage_change(current_total, previous_total)

            if change is not None:
                if change > 0:
                    trend = "up"
                elif change < 0:
                    trend = "down"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            prev_total = 0
            current_total = 0
            previous_total = 0
            change = None
            trend = "stable"

    # ranking
    valid = [s for s in statements if not s.get("is_missing")]

    totals = [(s.get("total") or s.get("value") or s.get("metric") or 0) for s in statements]
    max_val = max(totals) if totals else 1

    heatmap = [
        {
            "month": s["month"],
            "intensity": (s.get("total") or s.get("value") or s.get("metric") or 0) / max_val if max_val else 0
        }
        for s in statements
    ]

    best = max(valid, key=lambda x: (x.get("total") or x.get("value") or x.get("metric") or 0), default=None)
    worst = min(valid, key=lambda x: (x.get("total") or x.get("value") or x.get("metric") or 0), default=None)

    # =========================
    # YEAR OVER YEAR METRICS
    # =========================
    multi_year = {}
    forecast = None
    previous_total = None
    current_total = None

    if period_type == "year":
        prev_year = year - 1

        current_total = get_year_total(queryset, year, date_field)
        previous_total = get_year_total(queryset, prev_year, date_field)

        multi_year = {
            str(prev_year): previous_total,
            str(year): current_total,
            "growth": calculate_percentage_change(current_total, previous_total)
        }

    if period_type == "quarter":
        forecast = forecast_next(current_total or 0, change)

    # TARGET TRACKING
    target_meta = None
    if target:
        total_period = sum([(s.get("total") or s.get("value") or s.get("metric") or 0) for s in statements])

        target_meta = {
            "target": target,
            "actual": total_period,
            "achievement": total_period / target if target else None,
            "remaining": target - total_period if target else None
        }

    meta_obj = {
        "best_month": best,
        "worst_month": worst,
        "quarter_change": change if period_type == "quarter" else None,
        "trend": trend,
        "previous_quarter": {
            "year": prev_year if period_type == "quarter" else None,
            "quarter": prev_quarter if period_type == "quarter" else None,
            "total": previous_total if period_type == "quarter" else None,
        },
        "forecast": forecast if period_type == "quarter" else None,
        "target": target_meta,
        "heatmap": heatmap,
    }

    if period_type == "year":
        meta_obj["multi_year"] = multi_year
        meta_obj["kpis"] = {
            "total_period": sum([(s.get("total") or s.get("value") or s.get("metric") or 0) for s in valid]) if valid else 0,
            "average_month": (sum([(s.get("total") or s.get("value") or s.get("metric") or 0) for s in valid]) / len(valid)) if valid else 0,
            "best_value": max([(s.get("total") or s.get("value") or s.get("metric") or 0) for s in valid]) if valid else 0,
            "worst_value": min([(s.get("total") or s.get("value") or s.get("metric") or 0) for s in valid]) if valid else 0,
        }

    return {
        "data": {
            "view": period_type,
            "year": year,
            "quarter": quarter if period_type == "quarter" else None,
            "start": start,
            "end": end,
            "statements": statements,
            "kpis": quarter_kpis if period_type == "quarter" else None,
        },
        "meta": meta_obj
    }