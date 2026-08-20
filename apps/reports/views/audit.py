from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from apps.reports.models import AuditLog
from apps.reports.serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    queryset = AuditLog.objects.select_related(
        "user",
        "content_type"
    ).order_by("-timestamp")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "action",
        "user",
        "content_type",
    ]

    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
    ]

    ordering_fields = ["timestamp"]