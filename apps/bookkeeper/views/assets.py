from apps.bookkeeper.serializers import (
    AssetSerializer,
    CreateAssetSerializer
)
from apps.bookkeeper.models import Asset
from rest_framework import viewsets, permissions
from apps.bookkeeper.pagination import StandardPagination
from rest_framework.parsers import MultiPartParser, FormParser

class AssetView(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'create':
            return CreateAssetSerializer
        return AssetSerializer

    def get_queryset(self):
        return Asset.objects.filter(assembly=self.request.user.church)  # type: ignore

    # def update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     serializer = AssetSerializer(
    #         instance, data=request.data, partial=kwargs.pop("partial", False)
    #     )
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_update(serializer)
    #     return Response(serializer.data)