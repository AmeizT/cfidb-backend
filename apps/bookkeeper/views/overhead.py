from rest_framework import status
from django.db import IntegrityError, transaction
from rest_framework.response import Response
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from django.db.models import Count, Q
from apps.bookkeeper.models import Overhead, OverheadType
from apps.reports.models.audit import AuditLog
from apps.bookkeeper.serializers import OverheadBatchEntrySerializer, OverheadSerializer, OverheadTypeSerializer
from apps.bookkeeper.services import BatchEntryValidationError, create_overheads
from apps.bookkeeper.views.batch import active_assembly_or_error, batch_error_response, parse_batch_payload, validate_batch_entries
from rest_framework.viewsets import ModelViewSet
from apps.bookkeeper.category_matching import rank_financial_category_matches


from apps.uploads.mixins.overhead_template import OverheadTemplateMixin
from apps.uploads.services.overhead_upload import OverheadUploadService
from apps.uploads.mixins.upload_mixin import UploadExcelMixin

class OverheadViewSet(
    UploadExcelMixin,
    OverheadTemplateMixin,
    ModelViewSet
):
    """
    Handles CRUD for Overheads. Supports batch creation (list of overheads) 
    or single overhead creation. Automatically assigns assembly from user.
    """
    serializer_class = OverheadSerializer
    permission_classes = [permissions.IsAuthenticated]
    upload_service_class = OverheadUploadService

    @action(detail=False, methods=["get", "post"], url_path="types")
    def types(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        if request.method == "GET":
            queryset = OverheadType.objects.filter(is_active=True).filter(Q(is_global=True, assembly__isnull=True) | Q(is_global=False, assembly=assembly)).select_related("standard_category").order_by("is_global", "name")
            return Response(OverheadTypeSerializer(queryset, many=True).data)
        serializer = OverheadTypeSerializer(
            data=request.data,
            context={"request": request, "assembly": assembly},
        )
        serializer.is_valid(raise_exception=True)
        try:
            item = serializer.save(
                assembly=assembly, is_global=False, created_by=request.user,
            )
        except IntegrityError:
            return Response(
                {"name": ["This overhead type already exists for the active assembly."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(OverheadTypeSerializer(item).data, status=201)

    @action(detail=False, methods=["get"], url_path="types/suggestions")
    def type_suggestions(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"assembly_name": assembly.name, "assembly_matches": [], "standard_matches": []})

        assembly_options = OverheadType.objects.filter(
            assembly=assembly, is_global=False, is_active=True,
        ).select_related("standard_category").annotate(usage_count=Count("overheads"))
        standard_options = OverheadType.objects.filter(
            assembly__isnull=True, is_global=True, is_active=True,
        )
        assembly_matches = rank_financial_category_matches(query, assembly_options)
        standard_matches = rank_financial_category_matches(query, standard_options)
        return Response({
            "assembly_name": assembly.name,
            "assembly_matches": OverheadTypeSerializer(assembly_matches, many=True).data,
            "standard_matches": OverheadTypeSerializer(standard_matches, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        payload, error = parse_batch_payload(request)
        if error:
            return error
        entries, error = validate_batch_entries(OverheadBatchEntrySerializer, payload["entries"], request)
        if error:
            return error
        entries = [{**row, "overhead_type_id": row["overhead_type"].pk} for row in entries]
        try:
            created, totals = create_overheads(assembly=assembly, user=request.user, period=payload["period"], report_id=payload.get("report"), entries=entries)
        except BatchEntryValidationError as exc:
            return batch_error_response(exc)
        return Response({"count": len(created), "records": OverheadSerializer(created, many=True).data, "report_totals": totals}, status=201)

    def get_queryset(self): # type: ignore
        return Overhead.objects.filter(
            assembly=self.request.user.church # type: ignore
        ).select_related("overhead_type", "report")

    def create(self, request, *args, **kwargs):
        """
        Supports batch creation if the payload is a list.
        """
        # Check if the incoming data is a list (batch) or dict (single)
        is_many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        # Call perform_create (will log audit and handle multiple items)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Handles single or batch creation.
        Logs audit for each created item.
        """
        user = self.request.user if self.request.user.is_authenticated else None

        with transaction.atomic():
            instances = serializer.save()
            if not isinstance(instances, list):
                instances = [instances]

            for instance in instances:
                instance.log_audit(
                    user=user,
                    action=AuditLog.Action.CREATE,
                    old_data=None
                )
