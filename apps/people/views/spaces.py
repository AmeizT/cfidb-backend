from rest_framework import viewsets, permissions
from apps.people.models import Homecell
from apps.people.serializers import (
    HomecellSerializer,
    HomecellSummarySerializer
)

class HomecellView(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Homecell.objects.filter(
            church=self.request.user.church
        )

        if self.action == "list":
            return queryset.only("id", "group_name")

        return (
            queryset
            .select_related("leader", "church")
            .prefetch_related("members")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return HomecellSummarySerializer
        return HomecellSerializer