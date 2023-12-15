from django.shortcuts import render
from apps.strategic.models import StrategyLegacy, Strategy
from django_filters.rest_framework import DjangoFilterBackend
from apps.strategic.serializers import StrategyLegacySerializer, StrategySerializer
from rest_framework import permissions, views, viewsets, pagination


class StandardPagination(pagination.PageNumberPagination):
    page_size = 500
    page_size_query_param = "page_size"
    max_page_size = 1000000


class StrategyView(viewsets.ModelViewSet):
    queryset = Strategy.objects.all()
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    lookup_field = "slug"
    
    def get_queryset(self):
        return Strategy.objects.filter(branch=self.request.user.church) # type: ignore


class StrategyLegacyView(viewsets.ModelViewSet):
    queryset = StrategyLegacy.objects.all()
    serializer_class = StrategyLegacySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return StrategyLegacy.objects.filter(branch=self.request.user.church) # type: ignore
    
    
    