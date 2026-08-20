from apps.bookkeeper.serializers import (
    ExpenditureSerializer,
    FixedExpenditureSerializer,
    CreateFixedExpenditureSerializer,
)
from apps.bookkeeper.models import (
    Expenditure, 
    FixedExpenditure
)
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.bookkeeper.pagination import StandardPagination
from rest_framework.viewsets import ModelViewSet
from apps.uploads.mixins import ExpenditureTemplateMixin
from apps.uploads.services import ExpenditureUploadService
from apps.uploads.mixins.upload_mixin import UploadExcelMixin, UploadImageMixin
from apps.uploads.services.ocr import EXPENDITURE_FIELD_MAP
from apps.bookkeeper.serializers import ExpenditureBatchEntrySerializer
from apps.bookkeeper.services import BatchEntryValidationError, create_expenditures
from apps.bookkeeper.views.batch import active_assembly_or_error, batch_error_response, parse_batch_payload, validate_batch_entries

class ExpenditureView(
    UploadExcelMixin,
    UploadImageMixin,
    ExpenditureTemplateMixin,
    ModelViewSet
):
    queryset = Expenditure.objects.all()
    serializer_class = ExpenditureSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    upload_service_class = ExpenditureUploadService
    ocr_field_map = EXPENDITURE_FIELD_MAP

    @action(detail=False, methods=["post"], url_path="batch")
    def batch(self, request):
        assembly, error = active_assembly_or_error(request)
        if error:
            return error
        payload, error = parse_batch_payload(request, file_fields=("receipt",))
        if error:
            return error
        entries, error = validate_batch_entries(ExpenditureBatchEntrySerializer, payload["entries"], request)
        if error:
            return error
        try:
            created, totals = create_expenditures(assembly=assembly, user=request.user, period=payload["period"], report_id=payload.get("report"), entries=entries)
        except BatchEntryValidationError as exc:
            return batch_error_response(exc)
        return Response({"count": len(created), "records": ExpenditureSerializer(created, many=True).data, "report_totals": totals}, status=201)
    
    def get_queryset(self): # type: ignore
        return Expenditure.objects.filter(assembly=self.request.user.church)  # type: ignore
    
       
class RegularExpenditureView(viewsets.ModelViewSet):
    queryset = FixedExpenditure.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    http_method_names = ["get", "head", "options"]

    def get_serializer_class(self): # type: ignore
        if hasattr(self, 'action') and self.action == 'create':
            return CreateFixedExpenditureSerializer
        return FixedExpenditureSerializer

    def get_queryset(self): # type: ignore
        return FixedExpenditure.objects.filter(assembly=self.request.user.church)  # type: ignore
