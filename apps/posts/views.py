from apps.posts.models import Post, Comment
from rest_framework.response import Response
from rest_framework import pagination, permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.posts.serializers import CreatePostSerializer, PostSerializer, CreateCommentSerializer, UpdatePostSerializer

class PostPagination(pagination.PageNumberPagination):
    page_size = 2
    page_size_query_param = "page_size"
    max_page_size = 10000000

class PostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = PostPagination

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return CreatePostSerializer
        return PostSerializer


class UpdatePostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = UpdatePostSerializer
    permission_classes = [permissions.IsAuthenticated]


class CreatePostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = CreatePostSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]


class CreatePostCommentView(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CreateCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post', 'update', 'delete']
 
