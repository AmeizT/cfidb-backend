from datetime import timedelta
from django.utils.timezone import now
from django.utils.dateparse import parse_date


def resolve_date_range(request):
    today = now().date()

    range_param = request.query_params.get("range")
    start = request.query_params.get("start")
    end = request.query_params.get("end")

    # 1. Explicit custom range
    if start and end:
        start_date = parse_date(start)
        end_date = parse_date(end)

        if not start_date or not end_date:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")

        return start_date, end_date

    # 2. Relative ranges
    if range_param:
        if range_param == "7d":
            return today - timedelta(days=7), today

        if range_param == "1m":
            return today.replace(day=1), today

        if range_param == "2m":
            month = max(today.month - 2, 1)
            return today.replace(month=month, day=1), today

        if range_param == "3m":
            month = max(today.month - 3, 1)
            return today.replace(month=month, day=1), today

        if range_param == "1y":
            return today.replace(month=1, day=1), today

    # 3. Default fallback
    return today.replace(day=1), today