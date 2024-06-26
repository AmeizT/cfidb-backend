from apps.people.serializers import (
    AttendanceSerializer,
    CreateHomecellSerializer,
    CreateKindredSerializer,
    CreateAttendanceSerializer,
    CreateTallySerializer,
    HCAttendanceSerializer,
    HomecellSerializer,
    KindredSerializer,
    MemberSerializer,
    TallySerializer,
    
)
from django.shortcuts import render
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, pagination, status
from apps.people.models import (
    Attendance, 
    HCAttendance, 
    Homecell, 
    Kindred, 
    Member, 
    Tally
)


class StandardPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000000


class AttendanceView(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return CreateAttendanceSerializer
        return AttendanceSerializer

    def get_queryset(self):
        return Attendance.objects.filter(church=self.request.user.church)  # type: ignore
    

class HomecellView(viewsets.ModelViewSet):
    queryset = Homecell.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return CreateHomecellSerializer
        return HomecellSerializer

    def get_queryset(self):
        return Homecell.objects.filter(church=self.request.user.church)  # type: ignore
    

class CreateHomecellView(viewsets.ModelViewSet):
    queryset = Homecell.objects.all()
    serializer_class = CreateHomecellSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Homecell.objects.filter(church=self.request.user.church)  # type: ignore


class HCAttendanceView(viewsets.ModelViewSet):
    queryset = HCAttendance.objects.all()
    serializer_class = HCAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return HCAttendance.objects.filter(church=self.request.user.church)  # type: ignore
    
    
    # def create(self, request, *args, **kwargs):
    #     # Extract data from the request
    #     hcattendance_data = request.data.get('hcattendance', {})
    #     testimonies_data = request.data.get('testimonies', [])

    #     # Create HCAttendance object
    #     hcattendance_serializer = HCAttendanceSerializer(data=hcattendance_data)
    #     if hcattendance_serializer.is_valid():
    #         hcattendance = hcattendance_serializer.save()

    #         # Create Testimony objects associated with HCAttendance
    #         for testimony_data in testimonies_data:
    #             testimony_data['homecell'] = hcattendance.id  # Associate with HCAttendance
    #             testimony_serializer = TestimonySerializer(data=testimony_data)
    #             if testimony_serializer.is_valid():
    #                 testimony_serializer.save()
    #             else:
    #                 # Handle validation errors for Testimony objects
    #                 return Response(testimony_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    #         return Response({'message': 'HCAttendance and Testimonies created successfully'}, status=status.HTTP_201_CREATED)
    #     else:
    #         # Handle validation errors for HCAttendance object
    #         return Response(hcattendance_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberView(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "member_id"

    def get_queryset(self):
        return Member.objects.filter(church=self.request.user.church)  # type: ignore
    
    
class TallyView(viewsets.ModelViewSet):
    queryset = Tally.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):    
        if self.action == 'create':
            return CreateTallySerializer
        else:
            return TallySerializer
    
    def get_queryset(self):
        return Tally.objects.filter(branch=self.request.user.church)  # type: ignore
    
    
class CreateTallyView(viewsets.ModelViewSet):
    queryset = Tally.objects.all()
    serializer_class = CreateTallySerializer
    permission_classes = [permissions.IsAuthenticated]
    

    def get_queryset(self):
        return Tally.objects.filter(branch=self.request.user.church)  # type: ignore
    

class CreateKindredView(viewsets.ModelViewSet):
    queryset = Kindred.objects.all()
    serializer_class = CreateKindredSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "member_id"

    def get_queryset(self):
        return Kindred.objects.filter(church=self.request.user.church)  # type: ignore

       
class KindredView(viewsets.ModelViewSet):
    queryset = Kindred.objects.all()
    serializer_class = KindredSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "member_id"

    def get_queryset(self):
        return Kindred.objects.filter(church=self.request.user.church)  # type: ignore


class CreateMemberView(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    http_method_names = ["post", "put", "patch"]
    permission_classes = [permissions.IsAuthenticated]






    