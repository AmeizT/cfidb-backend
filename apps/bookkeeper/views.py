from django.shortcuts import render
from apps.bookkeeper.models import (
    Asset,
    Expenditure,
    Income,
    Payroll
)
from apps.bookkeeper.serializers import (
    AssetSerializer,
    ExpenditureSerializer, 
    IncomeSerializer,
    PayrollSerializer
)
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from apps.bookkeeper.pagination import StandardPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class AssetView(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Asset.objects.filter(church=self.request.user.church) # type: ignore
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AssetSerializer(
            instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    
class ExpenditureView(viewsets.ModelViewSet):
    queryset = Expenditure.objects.all()
    serializer_class = ExpenditureSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Expenditure.objects.filter(church=self.request.user.church) # type: ignore
    
    
class IncomeView(viewsets.ModelViewSet):
    queryset = Income.objects.all()
    serializer_class = IncomeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Income.objects.filter(church=self.request.user.church) # type: ignore
    
    
class PayrollView(viewsets.ModelViewSet):
    queryset = Payroll.objects.all()
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Asset.objects.filter(church=self.request.user.church) # type: ignore