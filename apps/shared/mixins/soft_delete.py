from django.db import transaction # type: ignore
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from apps.reports.models import AuditLog


class SoftDeleteMixin:
    def get_delete_description(self, instance):
        return f"{instance} soft deleted"

    def get_restore_description(self, instance):
        return f"{instance} restored"

    def _assert_report_editable(self, instance):
        report = getattr(instance, "report", None)
        if report is None:
            return
        from apps.reports.services.lifecycle import get_report_state

        if not get_report_state(report, self.request.user).is_editable:  # type: ignore
            raise PermissionDenied("This report is locked for editing.")

    def _all_objects_queryset(self):
        model = self.queryset.model  # type: ignore
        manager = getattr(model, "all_objects", model._base_manager)
        queryset = manager.all()
        user = self.request.user  # type: ignore
        if getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
            return queryset
        if getattr(user, "is_region_staff", False):
            return queryset.filter(assembly__zone__region__in=user.assigned_regions.all()).distinct()
        if getattr(user, "is_db_zone_staff", False):
            return queryset.filter(assembly__zone__in=user.assigned_zones.all()).distinct()
        assembly = getattr(user, "church", None)
        return queryset.filter(assembly=assembly) if assembly else queryset.none()

    def perform_destroy(self, instance):
        if not hasattr(instance, "is_deleted"):
            raise AttributeError(
                f"{instance.__class__.__name__} must define an is_deleted field."
            )

        if instance.is_deleted:
            return

        with transaction.atomic():
            self._assert_report_editable(instance)
            old_data = getattr(instance, "_capture_old_data", lambda: None)()
            instance.__class__.all_objects.filter(pk=instance.pk, is_deleted=False).update(
                is_deleted=True
            )
            instance.is_deleted = True

            report = getattr(instance, "report", None)
            if report is not None:
                from django.core.cache import cache
                report.recalculate_attendance_totals()
                cache.delete(f"report_cashflow_{report.pk}")

            instance.log_audit(
                user=self.request.user,  # type: ignore
                action=AuditLog.Action.DELETE,
                old_data=old_data,
                description=self.get_delete_description(instance),
            )


    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        instance = get_object_or_404(self._all_objects_queryset(), pk=pk, is_deleted=True)

        if not hasattr(instance, "is_deleted"):
            raise AttributeError(
                f"{instance.__class__.__name__} must define an is_deleted field."
            )

        if not instance.is_deleted:
            return Response(
                {"detail": "Record is already active."},
                status=400,
            )

        with transaction.atomic():
            self._assert_report_editable(instance)
            old_data = getattr(instance, "_capture_old_data", lambda: None)()
            instance.__class__.all_objects.filter(pk=instance.pk, is_deleted=True).update(
                is_deleted=False
            )
            instance.is_deleted = False

            report = getattr(instance, "report", None)
            if report is not None:
                from django.core.cache import cache
                report.recalculate_attendance_totals()
                cache.delete(f"report_cashflow_{report.pk}")

            instance.log_audit(
                user=request.user,
                action=AuditLog.Action.RESTORE,
                old_data=old_data,
                description=self.get_restore_description(instance),
            )

        return Response(self.get_serializer(instance).data)  # type: ignore
    

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "IDs must be a non-empty list."},
                status=400,
            )

        instances = list(self.get_queryset().filter( # type: ignore
            id__in=ids,
            is_deleted=False,
        ))

        deleted_ids = []
        errors = {}
        instances_by_id = {instance.pk: instance for instance in instances}
        for record_id in ids:
            instance = instances_by_id.get(record_id)
            if instance is None:
                errors[str(record_id)] = "Record was not found or is already deleted."
                continue
            try:
                with transaction.atomic():
                    self.perform_destroy(instance)
                deleted_ids.append(record_id)
            except (DjangoValidationError, PermissionDenied) as exc:
                errors[str(record_id)] = str(exc)

        return Response({
            "count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "errors": errors,
        }, status=200 if deleted_ids else 400)

    @action(detail=False, methods=["post"])
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "IDs must be a non-empty list."},
                status=400,
            )

        instances = list(self._all_objects_queryset().filter(
            id__in=ids,
            is_deleted=True,
        ))

        with transaction.atomic():
            for instance in instances:
                self._assert_report_editable(instance)
                old_data = getattr(instance, "_capture_old_data", lambda: None)()
                instance.__class__.all_objects.filter(pk=instance.pk).update(is_deleted=False)
                instance.is_deleted = False
                report = getattr(instance, "report", None)
                if report is not None:
                    from django.core.cache import cache
                    report.recalculate_attendance_totals()
                    cache.delete(f"report_cashflow_{report.pk}")
                instance.log_audit(
                    user=request.user,
                    action=AuditLog.Action.RESTORE,
                    old_data=old_data,
                    description=self.get_restore_description(instance),
                )

        return Response(
            {"count": len(instances), "restored_ids": [instance.pk for instance in instances]}
        )


# New class inserted after SoftDeleteMixin and before SoftDeleteQuerySet
class SoftDeleteQueryMixin:
    def get_queryset(self):
        queryset = super().get_queryset() # type: ignore
        return queryset.filter(is_deleted=False)


from django.db import models

class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def hard_delete(self):
        return super().delete()

    def soft_delete(self):
        return self.update(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted(self):
        return self.all_with_deleted().deleted()


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    objects = SoftDeleteManager()

    class Meta:
        abstract = True
