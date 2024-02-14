from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from apps.office.pagination import StandardPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.office.models import Circular, Meeting, Minutes, Strategy
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.office.serializers import (
    CircularSerializer,
    GetMinutesSerializer,
    MeetingSerializer, 
    MinutesSerializer, 
    StrategySerializer
)

class MeetingView(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        category = self.request.query_params.get('category', None)

        if category == "board" or category == "pastors":
            return Meeting.objects.filter(category=category)
        elif category == "workers" or category == "youth" or category == 'deacons' or category == 'elders':
            return Meeting.objects.filter(assembly=self.request.user.church, category=category)
        return Meeting.objects.filter(assembly=self.request.user.church)


class CircularView(viewsets.ModelViewSet):
    queryset = Circular.objects.all()
    serializer_class = CircularSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination
        
    def get_queryset(self):
        category = self.request.query_params.get('category', None)
        return Circular.objects.filter(category=category)
    
    
class MinutesView(viewsets.ModelViewSet):
    queryset = Minutes.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return MinutesSerializer
        return GetMinutesSerializer
    

class StrategyView(viewsets.ModelViewSet):
    queryset = Strategy.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Strategy.objects.filter(assembly=self.request.user.church)
    

# class CreateMinutesView(viewsets.ModelViewSet):
#     queryset = Minutes.objects.all()
#     serializer_class = CreateMinutesSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser]
#     pagination_class = StandardPagination

#     def get_queryset(self):
#         return Minutes.objects.filter(branch=self.request.user.church)