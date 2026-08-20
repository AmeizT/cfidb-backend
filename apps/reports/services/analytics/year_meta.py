def build_year_meta(statements, domain):
    valid = [s for s in statements if not s.get("is_missing")]

    # -------------------------
    # FINANCE DOMAIN
    # -------------------------
    if domain == "cashflow":
        total_income = sum(s.get("revenue_total", 0) for s in valid)
        total_expenses = sum(s.get("expense_total", 0) for s in valid)
        total_balance = sum(s.get("balance", 0) for s in valid)

        best = max(valid, key=lambda x: x.get("balance", 0), default=None)
        worst = min(valid, key=lambda x: x.get("balance", 0), default=None)

        trend = "up" if valid and valid[-1]["balance"] > valid[0]["balance"] else "down"

        return {
            "kpis": {
                "total_income": total_income,
                "total_expenditure": total_expenses,
                "net_cashflow": total_balance,
                "average_monthly_balance": total_balance / len(valid) if valid else 0,
            },
            "best_month": best,
            "worst_month": worst,
            "trend": trend,
            "missing": len([s for s in statements if s.get("is_missing")])
        }

    # -------------------------
    # TITHE DOMAIN
    # -------------------------
    if domain == "tithes":
        totals = [s.get("total", 0) for s in valid]

        # KPI-level median (domain aggregated median across months)
        median = (
            sum(s.get("median", 0) for s in valid) / len(valid)
            if valid else 0
        )

        total = sum(totals)
        givers = sum(s.get("givers", 0) for s in valid)

        # Advanced giver metrics
        total_members = max([s.get("members_total", 0) for s in valid], default=0)
        givers_share = (givers / total_members) if total_members else 0

        # Placeholder logic (can be improved with historical tracking)
        repeat_givers = sum(1 for s in valid if s.get("givers", 0) > 1)
        new_givers = sum(1 for s in valid if s.get("givers", 0) == 1)
        lapsed_givers = 0

        best = max(valid, key=lambda x: x.get("total", 0), default=None)
        worst = min(valid, key=lambda x: x.get("total", 0), default=None)

        trend = "up" if valid and valid[-1]["total"] > valid[0]["total"] else "down"

        return {
            "kpis": {
                "total": total,
                "givers": givers,
                "average": total / givers if givers else 0,
                "median": median,
                "givers_share": givers_share,
                "repeat_givers": repeat_givers,
                "new_givers": new_givers,
                "lapsed_givers": lapsed_givers,
                "retention_rate": (repeat_givers / givers) if givers else 0,
                "churn_rate": (lapsed_givers / givers) if givers else 0,
            },
            "best_month": best,
            "worst_month": worst,
            "trend": trend,
            "missing": len([s for s in statements if s.get("is_missing")])
        }

    # -------------------------
    # ATTENDANCE DOMAIN
    # -------------------------
    if domain == "attendance":
        total_adults = sum(s.get("total_adults", 0) for s in valid)
        total_children = sum(s.get("total_children", 0) for s in valid)
        total_visitors = sum(s.get("total_visitors", 0) for s in valid)

        total_attendance = sum(s.get("total", 0) for s in valid)

        # Median attendance (across months)
        totals = sorted([s.get("total", 0) for s in valid])
        n = len(totals)
        if n == 0:
            median = 0
        elif n % 2 == 1:
            median = totals[n // 2]
        else:
            median = (totals[n // 2 - 1] + totals[n // 2]) / 2

        best = max(valid, key=lambda x: x.get("total", 0), default=None)
        worst = min(valid, key=lambda x: x.get("total", 0), default=None)

        trend = "up" if valid and valid[-1].get("total", 0) > valid[0].get("total", 0) else "down"

        return {
            "kpis": {
                "total_adults": total_adults,
                "total_children": total_children,
                "total_visitors": total_visitors,
                "total_attendance": total_attendance,
                "average_attendance": total_attendance / len(valid) if valid else 0,
                "median_attendance": median,
            },
            "best_month": best,
            "worst_month": worst,
            "trend": trend,
            "missing": len([s for s in statements if s.get("is_missing")])
        }

    # -------------------------
    # FALLBACK (GENERIC)
    # -------------------------
    if domain not in ["cashflow", "tithes", "attendance"]:
        raise ValueError(f"Unsupported domain '{domain}'. Expected one of: finance, tithes, attendance")
    total = sum(s.get("total", 0) for s in valid)

    best = max(valid, key=lambda x: x.get("total", 0), default=None)
    worst = min(valid, key=lambda x: x.get("total", 0), default=None)

    trend = "up" if valid and valid[-1].get("total", 0) > valid[0].get("total", 0) else "down"

    return {
        "kpis": {
            "total": total,
            "average": total / len(valid) if valid else 0,
            "note": "fallback_generic_kpis_used"
        },
        "best_month": best,
        "worst_month": worst,
        "trend": trend,
        "missing": len([s for s in statements if s.get("is_missing")])
    }
