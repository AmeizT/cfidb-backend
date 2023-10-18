from apps.posts.models import Post
from rest_framework.response import Response
from rest_framework import permissions, viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from apps.posts.serializers import CreatePostSerializer, PostSerializer


class PostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]
    # parser_classes = [MultiPartParser, FormParser]

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data, many=True)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
    
class CreatePostView(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = CreatePostSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]
 
