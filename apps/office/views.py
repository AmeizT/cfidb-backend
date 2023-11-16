from django.shortcuts import render
from rest_framework.response import Response
from apps.office.models import Circular, Meeting, Minutes
from rest_framework import viewsets, permissions
from apps.office.pagination import StandardPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.office.serializers import (
    CircularSerializer,
    MeetingSerializer, MinutesSerializer, CreateMinutesSerializer
)

class MeetingView(viewsets.ModelViewSet):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Meeting.objects.filter(branch=self.request.user.church)


class CircularView(viewsets.ModelViewSet):
    queryset = Circular.objects.all()
    serializer_class = CircularSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Circular.objects.filter(branch=self.request.user.church)  


class MinutesView(viewsets.ModelViewSet):
    queryset = Minutes.objects.all()
    serializer_class = MinutesSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Minutes.objects.filter(branch=self.request.user.church) 
    

class CreateMinutesView(viewsets.ModelViewSet):
    queryset = Minutes.objects.all()
    serializer_class = CreateMinutesSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Minutes.objects.filter(branch=self.request.user.church)