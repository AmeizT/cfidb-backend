def build_kpi_response(year, statements, domain, extra_meta=None):
    """
    Unified response builder for ALL analytics domains
    """

    extra_meta = extra_meta or {}

    kpis = _build_domain_kpis(statements, domain)
    best, worst = _get_best_worst(statements, domain)
    trend = _get_trend(statements, domain)
    missing = len([s for s in statements if s.get("is_missing")])

    return {
        "data": {
            "view": "year",
            "year": year,
            "statements": statements,
        },
        "meta": {
            "kpis": kpis,
            "best_month": best,
            "worst_month": worst,
            "trend": trend,
            "missing": missing,
            **extra_meta
        }
    }



def _build_domain_kpis(statements, domain):
    valid = [s for s in statements if not s.get("is_missing")]

    if domain == "tithes":
        return _tithes_kpis(valid)

    if domain == "attendance":
        return _attendance_kpis(valid)

    if domain == "finance":
        return _finance_kpis(valid)

    raise ValueError(f"Unsupported domain: {domain}")


def _finance_kpis(valid):
    total_income = sum(s.get("revenue_total", 0) for s in valid)
    total_expense = sum(s.get("expense_total", 0) for s in valid)

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_cashflow": total_income - total_expense,
        "average_cashflow": (total_income - total_expense) / len(valid) if valid else 0,
    }


def _tithes_kpis(valid):
    total = sum(s.get("total", 0) for s in valid)
    givers = sum(s.get("givers", 0) for s in valid)

    medians = [s.get("median", 0) for s in valid if s.get("median") > 0]
    median = sorted(medians)[len(medians)//2] if medians else 0

    return {
        "total_tithes": total,
        "total_givers": givers,
        "average_tithe": total / givers if givers else 0,
        "median_tithe": median,
    }


def _attendance_kpis(valid):
    total_adults = sum(s.get("total_adults", 0) for s in valid)
    total_children = sum(s.get("total_children", 0) for s in valid)
    total_visitors = sum(s.get("total_visitors", 0) for s in valid)
    total_online = sum(s.get("online_viewers", 0) for s in valid)

    total_attendance = sum(s.get("total", 0) for s in valid)

    return {
        "total_adults": total_adults,
        "total_children": total_children,
        "total_visitors": total_visitors,
        "total_online_viewers": total_online,
        "total_attendance": total_attendance,
        "average_attendance": total_attendance / len(valid) if valid else 0,
    }


def _get_best_worst(statements, domain):
    valid = [s for s in statements if not s.get("is_missing")]

    key = {
        "finance": "balance",
        "tithes": "total",
        "attendance": "total"
    }[domain]

    if not valid:
        return None, None

    best = max(valid, key=lambda x: x.get(key, 0))
    worst = min(valid, key=lambda x: x.get(key, 0))

    return best, worst


def _get_trend(statements, domain):
    valid = [s for s in statements if not s.get("is_missing")]

    if len(valid) < 2:
        return "flat"

    key = {
        "finance": "balance",
        "tithes": "total",
        "attendance": "total"
    }[domain]

    first = valid[0].get(key, 0)
    last = valid[-1].get(key, 0)

    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"
