from apps.church.models import ( 
    Church, 
    Demographics,
    Member
)
from apps.church.serializers import (
    ChurchSerializer,
    DemographicSerializer,
    MemberSerializer 
)
from rest_framework.response import Response
from rest_framework import pagination, permissions, viewsets, status
from django_filters.rest_framework import DjangoFilterBackend


class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000000


class ChurchView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class AttendanceView(viewsets.ModelViewSet):
    queryset = Demographics.objects.all()
    serializer_class = DemographicSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    
    def get_queryset(self):
        return Demographics.objects.filter(church=self.request.user.church) # type: ignore
    
 
class MemberView(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    pagination_class = StandardPagination
    
    def get_queryset(self):
        return Member.objects.filter(church=self.request.user.church) # type: ignore



                                

    
    
    




