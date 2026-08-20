from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from apps.bookkeeper.models import Revenue, RevenueCategory
from apps.bookkeeper.serializers import RevenueBatchEntrySerializer, RevenueCategorySerializer, RevenueSerializer
from apps.bookkeeper.services import BatchEntryValidationError, create_revenues
from apps.bookkeeper.views.batch import active_assembly_or_error, batch_error_response, parse_batch_payload, validate_batch_entries
from apps.reports.models.audit import AuditLog
from rest_framework.viewsets import ModelViewSet
from apps.bookkeeper.category_matching import rank_financial_category_matches


from apps.uploads.mixins.revenue_template import RevenueTemplateMixin
from apps.uploads.services.revenue_upload import RevenueUploadService
from apps.uploads.mixins.upload_mixin import UploadExcelMixin

class RevenueViewSet(
    UploadExcelMixin,
    RevenueTemplateMixin,
    ModelViewSet
):
    serializer_class = RevenueSerializer
    permission_classes = [permissions.IsAuthenticated]
    upload_service_class = RevenueUploadService

    @action(detail=False, methods=["get", "post"], url_path="categories")
    def categories(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        if request.method == "GET":
            queryset = RevenueCategory.objects.filter(is_active=True).filter(
                Q(assembly=assembly, is_standard=False) |
                Q(assembly__isnull=True, is_standard=True)
            ).select_related("standard_category").order_by("is_standard", "name")
            return Response(RevenueCategorySerializer(queryset, many=True).data)
        serializer = RevenueCategorySerializer(
            data=request.data,
            context={"request": request, "assembly": assembly},
        )
        serializer.is_valid(raise_exception=True)
        try:
            category = serializer.save(
                assembly=assembly, is_standard=False, created_by=request.user,
            )
        except IntegrityError:
            return Response(
                {"name": ["This category already exists for the active assembly."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(RevenueCategorySerializer(category).data, status=201)

    @action(detail=False, methods=["get"], url_path="categories/suggestions")
    def category_suggestions(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"assembly_name": assembly.name, "assembly_matches": [], "standard_matches": []})

        assembly_options = RevenueCategory.objects.filter(
            assembly=assembly, is_standard=False, is_active=True,
        ).select_related("standard_category").annotate(usage_count=Count("revenues"))
        standard_options = RevenueCategory.objects.filter(
            assembly__isnull=True, is_standard=True, is_active=True,
        )
        assembly_matches = rank_financial_category_matches(query, assembly_options)
        standard_matches = rank_financial_category_matches(query, standard_options)
        return Response({
            "assembly_name": assembly.name,
            "assembly_matches": RevenueCategorySerializer(assembly_matches, many=True).data,
            "standard_matches": RevenueCategorySerializer(standard_matches, many=True).data,
        })

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        payload, error = parse_batch_payload(request, file_fields=("statement",))
        if error:
            return error
        entries, error = validate_batch_entries(RevenueBatchEntrySerializer, payload["entries"], request)
        if error:
            return error
        entries = [{**row, "category_id": row["category"].pk} for row in entries]
        try:
            created, totals = create_revenues(assembly=assembly, user=request.user, period=payload["period"], report_id=payload.get("report"), entries=entries)
        except BatchEntryValidationError as exc:
            return batch_error_response(exc)
        return Response({"count": len(created), "records": RevenueSerializer(created, many=True).data, "report_totals": totals}, status=201)

    def get_queryset(self): # type: ignore
        return Revenue.objects.filter(
            assembly=self.request.user.church # type: ignore
        ).select_related("category", "report")

    def create(self, request, *args, **kwargs):
        """
        Supports single or batch creation.
        """
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
        """
        Logs audit for single or batch creation.
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

    def perform_update(self, serializer):
        instance = serializer.instance
        old_data = instance._capture_old_data()
        updated_instance = serializer.save()

        user = self.request.user if self.request.user.is_authenticated else None

        updated_instance.log_audit(
            user=user,
            action=AuditLog.Action.UPDATE,
            old_data=old_data
        )
