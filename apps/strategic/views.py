from django.shortcuts import render
from apps.strategic.models import StrategyLegacy
from apps.strategic.serializers import StrategyLegacySerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, views, viewsets, pagination


class StandardPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000000


class StrategyView(viewsets.ModelViewSet):
    queryset = StrategyLegacy.objects.all()
    serializer_class = StrategyLegacySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    
    def get_queryset(self):
        return StrategyLegacy.objects.filter(branch=self.request.user.church) # type: ignore


class StrategyLegacyView(viewsets.ModelViewSet):
    queryset = StrategyLegacy.objects.all()
    serializer_class = StrategyLegacySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    
    def get_queryset(self):
        return StrategyLegacy.objects.filter(branch=self.request.user.church) # type: ignore
    
    

class StrategyLegacyTrackerView(viewsets.ModelViewSet):
    queryset = StrategyLegacy.objects.all()
    serializer_class = StrategyLegacySerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["branch__name"]
    pagination_class = StandardPagination
    
    