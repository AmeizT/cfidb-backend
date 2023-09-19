from django.shortcuts import render
from apps.projects.models import Project
from apps.projects.serializers import ProjectSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import pagination, permissions, views, viewsets

class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000000

class ProjectView(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    
    
    def get_queryset(self):
        return Project.objects.filter(church=self.request.user.church) # type: ignore
    
    
class ProjectTrackerView(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    pagination_class = StandardPagination