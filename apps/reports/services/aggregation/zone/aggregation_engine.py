from collections import defaultdict


def group_reports_by(reports, key_func):
    grouped = defaultdict(list)

    for report in reports:
        grouped[key_func(report)].append(report)

    return grouped