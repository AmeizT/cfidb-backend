from apps.people.serializers import (
    AttendanceSerializer, 
    MemberSerializer, 
    HCAttendanceSerializer,
    HomeCellSerializer
)
from django.shortcuts import render
from rest_framework.response import Response
from apps.people.models import Attendance, HCAttendance, Homecell, Members
from apps.people.permissions import IsAdminOrOverseer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, pagination, status


class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000000
    

class AttendanceView(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Attendance.objects.filter(church=self.request.user.church) # type: ignore
 
 
 
class HomeCellView(viewsets.ModelViewSet):
    queryset = Homecell.objects.all()
    serializer_class = HomeCellSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Homecell.objects.filter(church=self.request.user.church) # type: ignore
    
    
class HCAttendanceView(viewsets.ModelViewSet):
    queryset = HCAttendance.objects.all()
    serializer_class = HCAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'slug'
    
    def get_queryset(self):
        return HCAttendance.objects.filter(church=self.request.user.church) # type: ignore
           
    
class MemberView(viewsets.ModelViewSet):
    queryset = Members.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Members.objects.filter(church=self.request.user.church) # type: ignore
    
    
class CreateMemberView(viewsets.ModelViewSet):
    queryset = Members.objects.all()
    serializer_class = MemberSerializer
    http_method_names = ['post', 'put', 'patch']
    permission_classes = [permissions.AllowAny]
    
        
class CombineAttendanceView(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAdminOrOverseer]
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ["church__name"]
    
    
class CombineMemberView(viewsets.ModelViewSet):
    queryset = Members.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [IsAdminOrOverseer]
    filter_backends = [DjangoFilterBackend]
    # filterset_fields = ["church__name"]
    pagination_class = StandardPagination