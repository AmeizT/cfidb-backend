from django.shortcuts import render
from apps.resources.models import Resource
from rest_framework import permissions, views, viewsets
from apps.resources.serializers import ResourceSerializer


class ResourceView(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
