from apps.reports.helpers import (
    get_tithes_year
)
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.reports.helpers.get_cashflow_analytics import get_cashflow_year
from apps.reports.helpers.get_attendance_quarter import get_attendance_analytics

class ReportSummaryMixin:
    @action(detail=False, url_path="summary/tithes")
    def tithes_summary(self, request):
        assembly = request.user.church
        period = request.query_params.get("period")

        if not period:
            return Response({"detail": "period is required"}, status=400)

        period = int(period)

        return Response(get_tithes_year(assembly, period))
    
    @action(detail=False, url_path="summary/cashflow")
    def cashflow_year_summary(self, request):
        assembly = request.user.church
        period = request.query_params.get("period")

        if not period:
            return Response({"detail": "period is required"}, status=400)

        period = int(period)

        return Response(get_cashflow_year(assembly, period))
    
    @action(detail=False, url_path="summary/attendance")
    def attendance_summary(self, request):
        assembly = request.user.church
        period = request.query_params.get("period")

        if not period:
            return Response({"detail": "period is required"}, status=400)

        period = int(period)

        return Response(get_attendance_analytics(assembly, period))




    


    # @action(detail=False, url_path="summary/attendance")
    # def attendance_quarter(self, request):
    #     assembly = request.user.church
    #     year = int(request.query_params.get("period"))
    #     quarter = int(request.query_params.get("q"))

    #     return Response(get_attendance_quarter(assembly, year, quarter))


    # @action(detail=False, url_path="summary/cashflow")
    # def cashflow_quarter(self, request):
    #     assembly = request.user.church
    #     year = request.query_params.get("period")
    #     quarter = request.query_params.get("q")

    #     if not year:
    #         return Response({"detail": "period is required"}, status=400)

    #     if not quarter:
    #         return Response({"detail": "q (quarter) is required"}, status=400)

    #     year = int(year)
    #     quarter = int(quarter)

    #     return Response(finance_quarter_engine(assembly, year, quarter)) # type: ignore