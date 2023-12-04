from apps.posts.models import Post
from rest_framework.response import Response
from rest_framework import permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.posts.serializers import CreatePostSerializer, PostSerializer

class PostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]


class CreatePostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = CreatePostSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
 
