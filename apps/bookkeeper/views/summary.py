from datetime import date
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models.functions import ExtractMonth, ExtractYear
from apps.bookkeeper.models import Income
from apps.bookkeeper.serializers import FinanceSummarySerializer
from apps.bookkeeper.serializers import MonthlyIncomeSummarySerializer

class MonthlyIncomeSummaryView(viewsets.ViewSet):
    def list(self, request):
        church_income = (
            Income.objects.filter(church=request.user.church)
            .annotate(month=ExtractMonth('timestamp'), year=ExtractYear('timestamp'))
            .values('month', 'year')
            .annotate(
                total_offering=Sum('offering'),
                total_fundraising=Sum('fundraising'),
                total_thanksgiving=Sum('thanksgiving'),
                total_donations=Sum('donations'),
                total_income=Sum('offering') + Sum('fundraising') + Sum('thanksgiving') + Sum('donations')
            )
            .order_by('-year', '-month')
        )

        # Serialize and return data
        serializer = MonthlyIncomeSummarySerializer(church_income, many=True)
        return Response(serializer.data)

class FinanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        church = request.user.church
        year = int(request.query_params.get("year", date.today().year))
        month = int(request.query_params.get("month", date.today().month))

        data = FinanceSummarySerializer.get_data(church, year, month)
        return Response(data)
    

class FinanceYearlySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        church = request.user.church
        year = int(request.query_params.get("year", date.today().year))

        data = FinanceSummarySerializer.get_yearly_data(church, year)
        return Response(data)