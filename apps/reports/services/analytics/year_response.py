from apps.reports.services.analytics.year_meta import build_year_meta

def build_year_response(year, statements, domain, meta=None):
    domain_map = {
        "tithes": "tithes",
        "attendance": "attendance",
        "cashflow": "cashflow"
    }

    base_meta = build_year_meta(statements, domain=domain_map[domain])

    if meta:
        base_meta = {**base_meta, **meta}

    return {
        "data": {
            "view": "year",
            "year": year,
            "statements": statements
        },
        "meta": base_meta
    }