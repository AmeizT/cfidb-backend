from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.uploads.services.revenue_upload import RevenueUploadService
from apps.uploads.services.overhead_upload import OverheadUploadService
from apps.uploads.services.tithes_upload import TitheUploadService


class RevenueUploadMixin:
    upload_service_class = RevenueUploadService

    @action(detail=False, methods=["post"])
    def upload_excel(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = self.upload_service_class(user=request.user, file=file)
            result = service.process()
            return Response({"message": "Upload completed", **result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OverheadUploadMixin:
    upload_service_class = OverheadUploadService

    @action(detail=False, methods=["post"])
    def upload_excel(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = self.upload_service_class(user=request.user, file=file)
            result = service.process()
            return Response({"message": "Upload completed", **result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TitheUploadMixin:
    upload_service_class = TitheUploadService

    @action(detail=False, methods=["post"])
    def upload_excel(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = self.upload_service_class(user=request.user, file=file)
            result = service.process()
            return Response({"message": "Upload completed", **result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)