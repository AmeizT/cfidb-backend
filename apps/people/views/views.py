from apps.people.filters import MemberFilter
from apps.people.serializers.database import (
    AttendanceSerializer,
    CreateHomecellSerializer,
    CreateJuniorMemberSerializer,
    CreateAttendanceSerializer,
    CreateTallySerializer,
    HomecellSerializer,
    JuniorMemberSerializer,
    MemberSerializer,
    TallySerializer,
)
from django.shortcuts import render
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, pagination, status
from apps.people.models import (
    Attendance, 
    Homecell, 
    JuniorMember, 
    Member, 
    Tally
)

class StandardPagination(pagination.PageNumberPagination):
    page_size = 100000
    page_size_query_param = "page_size"
    max_page_size = 100000000000000


class AttendanceView(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
 
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CreateAttendanceSerializer
        return AttendanceSerializer
    
    def get_queryset(self):
        if self.action == 'list':
            category = self.request.query_params.get('category', None)

            if category:
                return Attendance.objects.filter(church=self.request.user.church, category=category)
            return Attendance.objects.filter(church=self.request.user.church)
        
        return Attendance.objects.all()


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


# class HCAttendanceView(viewsets.ModelViewSet):
#     queryset = HCAttendance.objects.all()
#     serializer_class = HCAttendanceSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     lookup_field = "slug"

#     def get_queryset(self):
#         return HCAttendance.objects.filter(church=self.request.user.church) 
    
    
#     def create(self, request, *args, **kwargs):
#         # Extract data from the request
#         hcattendance_data = request.data.get('hcattendance', {})
#         testimonies_data = request.data.get('testimonies', [])

#         # Create HCAttendance object
#         hcattendance_serializer = HCAttendanceSerializer(data=hcattendance_data)
#         if hcattendance_serializer.is_valid():
#             hcattendance = hcattendance_serializer.save()

#             # Create Testimony objects associated with HCAttendance
#             for testimony_data in testimonies_data:
#                 testimony_data['homecell'] = hcattendance.id  # Associate with HCAttendance
#                 testimony_serializer = TestimonySerializer(data=testimony_data)
#                 if testimony_serializer.is_valid():
#                     testimony_serializer.save()
#                 else:
#                     # Handle validation errors for Testimony objects
#                     return Response(testimony_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#             return Response({'message': 'HCAttendance and Testimonies created successfully'}, status=status.HTTP_201_CREATED)
#         else:
#             # Handle validation errors for HCAttendance object
#             return Response(hcattendance_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MemberView(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberFilter
    lookup_field = "member_id"

    def get_queryset(self):
        return Member.objects.filter(assembly=self.request.user.church)
    
    
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
    
       
class JuniorMemberView(viewsets.ModelViewSet):
    queryset = JuniorMember.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "member_id"

    def get_serializer_class(self):    
        if self.action == 'create' or self.action == 'partial_update':
            return CreateJuniorMemberSerializer
        else:
            return JuniorMemberSerializer
        
    def get_queryset(self):
        return JuniorMember.objects.filter(church=self.request.user.church)  # type: ignore


class CreateMemberView(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    http_method_names = ["post", "put", "patch"]
    permission_classes = [permissions.IsAuthenticated]






    