from apps.forum.models import Changelog
from rest_framework.response import Response
from rest_framework import permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.forum.serializers import ChangelogSerializer, ChangelogDataSerializer

class ChangelogView(viewsets.ModelViewSet):
    queryset = Changelog.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return ChangelogSerializer
        return ChangelogDataSerializer
    