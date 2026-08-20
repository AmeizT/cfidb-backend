def build_quarter_response(*, year, quarter, start, end, statements, meta=None):
    return {
        "data": {
            "view": "quarter",
            "year": year,
            "quarter": quarter,
            "start": start,
            "end": end,
            "statements": statements,
        },
        "meta": meta or {}
    }