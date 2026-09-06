from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework.decorators import action
from apps.reports.models.audit import AuditLog
from apps.reports.services.lifecycle import get_report_state
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404


class FinancialViewSet(viewsets.ModelViewSet):
    """
    Base viewset for all financial models (Tithe, Revenue, Overhead, etc.)
    Handles assembly filtering, trash filtering, audit logging, soft delete, and restore.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filters by user assembly/church and optional trash query param
        """
        user = self.request.user
        show_trashed = self.request.query_params.get("trash") # type: ignore

        # Must set `self.queryset` in child class. Prefer all_objects when a
        # financial model has a soft-trash manager, otherwise use the model's
        # default manager.
        model = self.queryset.model # type: ignore
        manager = getattr(model, "all_objects", model.objects)
        queryset = manager.filter(
            assembly=user.church # type: ignore
        ).select_related("report")

        if show_trashed == "true":
            queryset = queryset.filter(is_trash=True)
        else:
            queryset = queryset.filter(is_trash=False)

        field_names = {field.name for field in queryset.model._meta.fields}
        year = self.request.query_params.get("year") # type: ignore
        month = self.request.query_params.get("month") # type: ignore
        search = self.request.query_params.get("search") # type: ignore
        ordering = self.request.query_params.get("ordering") # type: ignore
        status_filter = self.request.query_params.get("status") # type: ignore

        if "timestamp" in field_names and year:
            queryset = queryset.filter(timestamp__year=year)

        if "timestamp" in field_names and month:
            queryset = queryset.filter(timestamp__month=month)

        if "status" in field_names and status_filter:
            if status_filter == "active":
                queryset = queryset.exclude(status="VOIDED")
            elif status_filter == "voided":
                queryset = queryset.filter(status="VOIDED")

        if search:
            search_query = Q()

            if "reference_code" in field_names:
                search_query |= Q(reference_code__icontains=search)

            if "notes" in field_names:
                search_query |= Q(notes__icontains=search)

            if "member" in field_names:
                search_query |= (
                    Q(member__first_name__icontains=search)
                    | Q(member__last_name__icontains=search)
                    | Q(member__email__icontains=search)
                )

            if search_query:
                queryset = queryset.filter(search_query)

        if ordering:
            allowed_ordering = {
                "timestamp",
                "-timestamp",
                "created_at",
                "-created_at",
                "amount",
                "-amount",
            }
            requested = [
                field for field in ordering.split(",")
                if field in allowed_ordering and field.lstrip("-") in field_names
            ]

            if requested:
                queryset = queryset.order_by(*requested)

        return queryset

    # -----------------------------
    # Create / Batch Create
    # -----------------------------
    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(
            data=request.data,
            many=is_many
        )
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        user = self.request.user

        with transaction.atomic():
            save_kwargs = {"assembly": user.church}
            model = getattr(getattr(serializer, "Meta", None), "model", None)
            if model is None and hasattr(serializer, "child"):
                model = getattr(getattr(serializer.child, "Meta", None), "model", None)
            if model is not None and any(field.name == "created_by" for field in model._meta.fields):
                save_kwargs["created_by"] = user
            instances = serializer.save(**save_kwargs)

            if not isinstance(instances, list):
                instances = [instances]

            for instance in instances:
                # AuditLogMixin handles action / old_data / new_data
                instance.log_audit(
                    user=user,
                    action=AuditLog.Action.CREATE
                )

    # -----------------------------
    # Update
    # -----------------------------
    def perform_update(self, serializer):
        instance = serializer.instance
        report = getattr(instance, "report", None)
        if report is not None and not get_report_state(report, self.request.user).is_editable:
            raise PermissionDenied("This report is locked for editing.")
        old_data = instance._capture_old_data()

        updated_instance = serializer.save()

        updated_instance.log_audit(
            user=self.request.user,
            action=AuditLog.Action.UPDATE,
            old_data=old_data
        )

    # -----------------------------
    # Soft Delete
    # -----------------------------
    def perform_destroy(self, instance):
        user = self.request.user
        report = getattr(instance, "report", None)
        if report is not None and not get_report_state(report, user).is_editable:
            raise PermissionDenied("This report is locked for editing.")
        old_data = instance._capture_old_data()

        instance.delete(user=user)
        instance.log_audit(
            user=user,
            action=AuditLog.Action.DELETE,
            old_data=old_data
        )

    @action(detail=False, methods=["post"], url_path="bulk_delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "IDs must be a non-empty list."}, status=400)

        instances_by_id = {
            instance.pk: instance
            for instance in self.get_queryset().filter(pk__in=ids, is_trash=False)
        }
        deleted_ids = []
        errors = {}
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

    # -----------------------------
    # Restore trashed item
    # -----------------------------
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        user = self.request.user
        model = self.queryset.model
        manager = getattr(model, "all_objects", model.objects)
        instance = get_object_or_404(
            manager.select_related("report"),
            pk=pk,
            assembly=user.church,
            is_trash=True,
        )
        report = getattr(instance, "report", None)
        if report is not None and not get_report_state(report, user).is_editable:
            raise PermissionDenied("This report is locked for editing.")

        old_data = instance._capture_old_data()
        try:
            instance.restore(user=user)
        except IntegrityError as exc:
            raise ValidationError({
                "detail": "This record conflicts with an active replacement and cannot be restored."
            }) from exc
        instance.log_audit(
            user=user,
            action=AuditLog.Action.RESTORE,
            old_data=old_data
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
