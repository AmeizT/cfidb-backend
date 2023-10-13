from django.shortcuts import render
from apps.strategy.models import Strategy
from apps.strategy.serializers import StrategySerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, views, viewsets, pagination


class StandardPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000000

class StrategyView(viewsets.ModelViewSet):
    queryset = Strategy.objects.all()
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    
    def get_queryset(self):
        return Strategy.objects.filter(church=self.request.user.church) # type: ignore
    
    

class StrategyTrackerView(viewsets.ModelViewSet):
    queryset = Strategy.objects.all()
    serializer_class = StrategySerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    pagination_class = StandardPagination
    
    