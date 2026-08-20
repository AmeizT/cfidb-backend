from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.reports.models import AuditLog

class SoftDeleteMixin:
    def perform_destroy(self, instance):
        with transaction.atomic():
            old_data = getattr(instance, "_capture_old_data", lambda: None)()

            instance.is_deleted = True
            instance.save()

            description = (
                f"{instance.service_type} service soft deleted | "
                f"Headcount: {instance.headcount} | "
                f"New Converts: {instance.total_new_converts}"
            )

            instance.log_audit(
                user=self.request.user, # type: ignore
                action=AuditLog.Action.DELETE,
                old_data=old_data,
                description=description
            )

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = self.get_object()

        with transaction.atomic():
            old_data = getattr(instance, "_capture_old_data", lambda: None)()

            instance.is_deleted = False
            instance.save()

            description = (
                f"{instance.service_type} service restored | "
                f"Headcount: {instance.headcount} | "
                f"New Converts: {instance.total_new_converts}"
            )

            instance.log_audit(
                user=request.user,
                action=AuditLog.Action.RESTORE,
                old_data=old_data,
                description=description
            )

        return Response(self.get_serializer(instance).data)

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])

        if not isinstance(ids, list) or not ids:
            return Response({"detail": "IDs must be a non-empty list."}, status=400)

        instances = self.get_queryset().filter(id__in=ids)

        with transaction.atomic():
            for instance in instances:
                self.perform_destroy(instance)

        return Response({"detail": f"{instances.count()} deleted"})

    @action(detail=False, methods=['post'])
    def bulk_restore(self, request):
        ids = request.data.get('ids', [])

        if not isinstance(ids, list) or not ids:
            return Response({"detail": "IDs must be a non-empty list."}, status=400)

        instances = self.get_queryset().filter(id__in=ids)

        with transaction.atomic():
            for instance in instances:
                instance.is_deleted = False
                instance.save()

        return Response({"detail": f"{instances.count()} restored"})
