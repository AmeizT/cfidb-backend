from django.shortcuts import render
from rest_framework.response import Response
from apps.office.models import Document, Meeting, Minutes
from rest_framework import viewsets, permissions
from apps.office.pagination import StandardPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.office.serializers import (
    DocumentSerializer,
    MeetingSerializer, MinutesSerializer, CreateMinutesSerializer
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
            return Meeting.objects.filter(branch=self.request.user.church, category=category)
        return Meeting.objects.filter(branch=self.request.user.church)


class DocumentView(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination
        
    def get_queryset(self):
        category = self.request.query_params.get('category', None)

        if category == "strategy":
            return Document.objects.filter(branch=self.request.user.church, category="strategy")
        elif category:
            return Document.objects.filter(category=category)
        return self.queryset
    
    
class MinutesView(viewsets.ModelViewSet):
    queryset = Minutes.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return CreateMinutesSerializer
        return MinutesSerializer
    

class CreateMinutesView(viewsets.ModelViewSet):
    queryset = Minutes.objects.all()
    serializer_class = CreateMinutesSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Minutes.objects.filter(branch=self.request.user.church)