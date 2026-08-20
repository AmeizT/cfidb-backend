from django.db.models import Sum, Count
from calendar import month_name

def build_time_statements(
    *,
    queryset,
    year: int,
    months: list,
    date_field="timestamp",
    value_fields=None,
    extra_aggregations=None,
):
    value_fields = value_fields or {}
    extra_aggregations = extra_aggregations or {}

    annotations = {
        key: Sum(field)
        for key, field in value_fields.items()
    }
    annotations.update(extra_aggregations)

    monthly = (
        queryset
        .values(f"{date_field}__month")
        .annotate(**annotations)
    )

    data_map = {
        item[f"{date_field}__month"]: item
        for item in monthly
    }

    statements = []

    for m in months:
        item = data_map.get(m)

        row = {
            "month": m,
            "label": month_name[m],
            "is_missing": item is None,
        }

        for key in annotations.keys():
            row[key] = item.get(key, 0) if item else 0

        statements.append(row)

    return statements