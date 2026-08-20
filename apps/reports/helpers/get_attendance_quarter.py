from apps.reports.services.analytics import build_attendance_year

def get_attendance_analytics(assembly, year):
    return build_attendance_year(assembly=assembly, year=year)