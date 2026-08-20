from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import action
from apps.reports.models.audit import AuditLog


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
            instances = serializer.save(
                assembly=user.church # type: ignore
            )

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
        old_data = instance._capture_old_data()

        instance.delete()
        instance.log_audit(
            user=user,
            action=AuditLog.Action.SOFT_DELETE, # type: ignore
            old_data=old_data
        )

    # -----------------------------
    # Restore trashed item
    # -----------------------------
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        user = self.request.user
        instance = self.get_object()

        old_data = instance._capture_old_data()
        instance.restore()
        instance.log_audit(
            user=user,
            action=AuditLog.Action.RESTORED,
            old_data=old_data
        )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
