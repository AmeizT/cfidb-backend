from apps.churches.models import Church, ImageUpload
from rest_framework.response import Response
from apps.churches.permissions import IsAdminUserOrOverseer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import pagination, permissions, viewsets, status
from apps.churches.serializers import ChurchSerializer, ChurchTrackerSerializer, ImageUploadSerializer
from rest_framework.parsers import MultiPartParser, FormParser


class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000000


class ChurchView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    # permission_classes = [permissions.IsAuthenticated]
    lookup_field = "name"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListChurchesView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchTrackerSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "name"
    http_method_names = ["head", "get"]


class ImageUploadView(viewsets.ModelViewSet):
    queryset = ImageUpload.objects.all()
    serializer_class = ImageUploadSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]
