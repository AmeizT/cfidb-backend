from django.shortcuts import render
from apps.projects.models import Project
from rest_framework import permissions, views, viewsets
from apps.projects.serializers import ProjectSerializer

class ProjectView(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Project.objects.filter(church=self.request.user.church) # type: ignore