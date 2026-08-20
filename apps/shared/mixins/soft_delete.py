from django.db import transaction # type: ignore
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.reports.models import AuditLog


class SoftDeleteMixin:
    def get_delete_description(self, instance):
        return f"{instance} soft deleted"

    def get_restore_description(self, instance):
        return f"{instance} restored"

    def perform_destroy(self, instance):
        if not hasattr(instance, "is_deleted"):
            raise AttributeError(
                f"{instance.__class__.__name__} must define an is_deleted field."
            )

        if instance.is_deleted:
            return

        with transaction.atomic():
            old_data = getattr(instance, "_capture_old_data", lambda: None)()

            instance.is_deleted = True
            instance.save(update_fields=["is_deleted"])

            instance.log_audit(
                user=self.request.user,  # type: ignore
                action=AuditLog.Action.DELETE,
                old_data=old_data,
                description=self.get_delete_description(instance),
            )


    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        instance = self.get_object()  # type: ignore

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
            old_data = getattr(instance, "_capture_old_data", lambda: None)()

            instance.is_deleted = False
            instance.save(update_fields=["is_deleted"])

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

        instances = self.get_queryset().filter( # type: ignore
            id__in=ids,
            is_deleted=False,
        )

        with transaction.atomic():
            for instance in instances:
                self.perform_destroy(instance)

        return Response(
            {"detail": f"{instances.count()} deleted"}
        )

    @action(detail=False, methods=["post"])
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "IDs must be a non-empty list."},
                status=400,
            )

        instances = self.get_queryset().filter( # type: ignore
            id__in=ids,
            is_deleted=True,
        )

        with transaction.atomic():
            for instance in instances:
                instance.is_deleted = False
                instance.save(update_fields=["is_deleted"])

        return Response(
            {"detail": f"{instances.count()} restored"}
        )


# New class inserted after SoftDeleteMixin and before SoftDeleteQuerySet
class SoftDeleteQueryMixin:
    def get_queryset(self):
        queryset = super().get_queryset() # type: ignore

        if "is_deleted" not in self.request.query_params: # type: ignore
            queryset = queryset.filter(is_deleted=False)

        return queryset


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