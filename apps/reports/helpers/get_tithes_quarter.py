from apps.reports.services.analytics.tithes_engine import build_tithes_year

def get_tithes_year(assembly, year):
    return build_tithes_year(assembly=assembly, year=year)


