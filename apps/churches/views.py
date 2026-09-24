from apps.churches.models import Church
from rest_framework.response import Response
from apps.churches.permissions import IsAdminUserOrOverseer, CanCreateAssembly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import pagination, permissions, viewsets, status
from apps.churches.serializers import ChurchAppearanceSerializer, ChurchSerializer, CreateChurchSerializer
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser

class StandardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000000


class ChurchView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    def get_serializer_class(self):
        return CreateChurchSerializer if self.action == "create" else ChurchSerializer

    @action(detail=False, methods=["get"], url_path="create-options", permission_classes=[CanCreateAssembly])
    def create_options(self, request):
        from apps.churches.country_defaults import country_options
        from apps.users.models import User
        return Response({
            "countries": country_options(),
            "pastors": [{"id": user.pk, "name": user.full_name} for user in
                        User.objects.filter(is_active=True, roles__name__in=["Pastor", "Senior Pastor"]).distinct()],
        })

    def get_permissions(self):
        if self.action == "create":
            return [CanCreateAssembly()]
        if self.action == "partial_update":
            return [IsAdminUserOrOverseer()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=["patch"],
        url_path="appearance",
        permission_classes=[IsAdminUserOrOverseer],
    )
    
    def appearance(self, request):
        assembly = request.user.church
        if assembly is None:
            return Response(
                {"detail": "No active assembly is selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChurchAppearanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assembly.avatar_fallback = serializer.validated_data["avatar_fallback"]
        assembly.save(update_fields=["avatar_fallback", "updated_at"])
        return Response({"avatar_fallback": assembly.avatar_fallback})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data, many=True)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListChurchesView(viewsets.ModelViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "name"
    http_method_names = ["head", "get"]


# class ImageUploadView(viewsets.ModelViewSet):
#     queryset = ImageUpload.objects.all()
#     serializer_class = ImageUploadSerializer
#     permission_classes = [permissions.AllowAny]
#     parser_classes = [MultiPartParser, FormParser]
