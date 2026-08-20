from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.reports.models import ReportSectionStatus
from apps.reports.serializers.section_status import ReportSectionSerializer
from apps.reports.services.lifecycle import get_section_source, set_section_status


class ReportSectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = ReportSectionStatus.objects.select_related("report__assembly")
        if user.is_superuser or getattr(user, "is_admin", False) or getattr(user, "is_db_staff", False):
            return queryset
        if getattr(user, "is_db_zone_staff", False):
            return queryset.filter(report__assembly__zone__in=user.assigned_zones)
        if not getattr(user, "church_id", None):
            raise PermissionDenied("No active assembly selected.")
        return queryset.filter(report__assembly_id=user.church_id)

    def _change(self, request, section, status):
        changed = set_section_status(
            report=section.report,
            section_key=section.section,
            status=status,
            actor=request.user,
            skip_reason_code=request.data.get("skip_reason_code") or request.data.get("reason"),
            skip_reason_detail=request.data.get("skip_reason_detail") or request.data.get("notes"),
            no_activity_note=request.data.get("no_activity_note"),
        )
        payload = self.get_serializer(changed).data
        payload["source"] = get_section_source(changed.report, changed.section)
        return Response(payload)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        return self._change(request, self.get_object(), ReportSectionStatus.Status.IN_PROGRESS)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._change(request, self.get_object(), ReportSectionStatus.Status.COMPLETED)

    @action(detail=True, methods=["post"])
    def no_activity(self, request, pk=None):
        return self._change(request, self.get_object(), ReportSectionStatus.Status.NO_ACTIVITY)

    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        return self._change(request, self.get_object(), ReportSectionStatus.Status.SKIPPED)

    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        return self._change(request, self.get_object(), ReportSectionStatus.Status.NOT_STARTED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Compatibility alias for older clients."""
        return self.complete(request, pk=pk)
