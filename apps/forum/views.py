from apps.forum.models import Forum, Reply
from rest_framework.response import Response
from rest_framework import permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.forum.serializers import ForumSerializer, ForumDataSerializer, ForumReplySerializer

class ForumDataView(viewsets.ModelViewSet):
    queryset = Forum.objects.all()
    serializer_class = ForumDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "slug"
    

class ForumView(viewsets.ModelViewSet):
    queryset = Forum.objects.all()
    serializer_class = ForumSerializer
    permission_classes = [permissions.IsAuthenticated]


class ForumReplyView(viewsets.ModelViewSet):
    queryset = Reply.objects.all()
    serializer_class = ForumReplySerializer
    permission_classes = [permissions.IsAuthenticated]