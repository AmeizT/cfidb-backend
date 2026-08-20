from typing import TypedDict, List, Dict, Any, Optional, Literal


# -------------------------------------------------
# TYPES
# -------------------------------------------------

Domain = Literal["tithes", "attendance", "finance"]


class Statement(TypedDict, total=False):
    month: int
    label: str
    is_missing: bool

    # shared metrics
    total: float
    balance: float

    # attendance
    total_adults: int
    total_children: int
    total_visitors: int
    online_viewers: int

    # tithes
    givers: int


class KPIResult(TypedDict, total=False):
    primary_total: float
    secondary_total: float
    average: float
    median: float
    net: float

    # optional extras
    repeat_givers: int
    new_givers: int
    lapsed_givers: int


class InsightResult(TypedDict):
    trend: str
    best_month: Optional[Statement]
    worst_month: Optional[Statement]
    missing: int


class KPIResponse(TypedDict):
    data: Dict[str, Any]
    meta: Dict[str, Any]


# -------------------------------------------------
# ENTRY POINT
# -------------------------------------------------

def build_kpi_response(
    *,
    year: int,
    statements: List[Statement],
    domain: Domain,
    extra_meta: Optional[Dict[str, Any]] = None,
) -> KPIResponse:
    """
    Unified analytics response builder
    """

    kpis = build_domain_kpis(statements, domain)
    ytd = build_ytd(statements, domain)
    insights = build_insights(statements, domain)

    meta = {
        # "kpis": kpis,
        # "ytd": ytd,
        "insights": insights,
    }

    if extra_meta:
        meta.update(extra_meta)

    return {
        "data": {
            "year": year,
            "statements": statements,
        },
        "meta": meta,
    }


def build_domain_kpis(statements: List[Statement], domain: Domain) -> KPIResult:
    builders = {
        "tithes": _tithe_kpis,
        "attendance": _attendance_kpis,
        "finance": _finance_kpis,
    }

    try:
        return builders[domain](statements)
    except KeyError:
        raise ValueError(f"Unsupported domain '{domain}'")
    

def _tithe_kpis(statements: List[Statement]) -> KPIResult:
    valid = [s for s in statements if not s.get("is_missing")]

    total = sum(s.get("total", 0) for s in valid)
    givers = sum(s.get("givers", 0) for s in valid)

    values = sorted(s.get("total", 0) for s in valid)
    median = _median(values)

    return {
        "primary_total": total,
        "secondary_total": givers,
        "average": total / len(valid) if valid else 0,
        "median": median,

        # optional intelligence
        "repeat_givers": sum(s.get("repeat_givers", 0) for s in valid),
        "new_givers": sum(s.get("new_givers", 0) for s in valid),
        "lapsed_givers": sum(s.get("lapsed_givers", 0) for s in valid),
    }


def _attendance_kpis(statements: List[Statement]) -> KPIResult:
    valid = [s for s in statements if not s.get("is_missing")]

    total = sum(s.get("total", 0) for s in valid)

    values = sorted(s.get("total", 0) for s in valid)
    median = _median(values)

    return {
        "primary_total": total,
        "secondary_total": None,  # optional (guests if needed) # type: ignore
        "average": total / len(valid) if valid else 0,
        "median": median,
    }


def _finance_kpis(statements: List[Statement]) -> KPIResult:
    valid = [s for s in statements if not s.get("is_missing")]

    total_income = sum(s.get("revenue_total", 0) for s in valid)
    total_expense = sum(s.get("expense_total", 0) for s in valid)
    net = sum(s.get("balance", 0) for s in valid)

    return {
        "primary_total": total_income,
        "secondary_total": total_expense,
        "net": net,
    }


def build_ytd(statements: List[Statement], domain: Domain) -> Dict[str, float]:
    valid = [s for s in statements if not s.get("is_missing")]

    if domain == "finance":
        return {
            "primary_total": sum(s.get("revenue_total", 0) for s in valid),
            "secondary_total": sum(s.get("expense_total", 0) for s in valid),
            "net": sum(s.get("balance", 0) for s in valid),
        }

    return {
        "primary_total": sum(s.get("total", 0) for s in valid),
    }


def build_insights(statements: List[Statement], domain: Domain) -> InsightResult:
    valid = [s for s in statements if not s.get("is_missing")]

    if not valid:
        return {
            "trend": "flat",
            "best_month": None,
            "worst_month": None,
            "missing": len(statements),
        }

    key = _metric_key(domain)

    best = max(valid, key=lambda x: x.get(key, 0))
    worst = min(valid, key=lambda x: x.get(key, 0))

    first = valid[0].get(key, 0)
    last = valid[-1].get(key, 0)

    trend = "up" if last > first else "down" if last < first else "flat"

    return {
        "trend": trend,
        "best_month": best,
        "worst_month": worst,
        "missing": sum(1 for s in statements if s.get("is_missing")),
    }


def _metric_key(domain: Domain) -> str:
    return {
        "tithes": "total",
        "attendance": "total",
        "finance": "balance",
    }.get(domain, "total")


def _median(values: List[float]) -> float:
    n = len(values)
    if n == 0:
        return 0
    if n % 2 == 1:
        return values[n // 2]
    return (values[n // 2 - 1] + values[n // 2]) / 2
