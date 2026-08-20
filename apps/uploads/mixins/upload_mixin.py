import json

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.uploads.services.ocr import OcrImageUploadService

class UploadExcelMixin:
    upload_service_class = None  # must be set in child

    @action(detail=False, methods=["post"])
    def upload_excel(self, request):
        if not self.upload_service_class:
            return Response(
                {"error": "Upload service not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file uploaded"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            service = self.upload_service_class(
                user=request.user,
                file=file
            )

            result = service.process()

            return Response({
                "message": "Upload completed",
                **result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=400)


class UploadImageMixin:
    upload_service_class = None
    image_upload_service_class = OcrImageUploadService
    ocr_field_map = None

    @action(detail=False, methods=["post"], url_path="upload-image")
    def upload_image(self, request):
        if not self.upload_service_class:
            return Response(
                {"error": "Upload service not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not self.ocr_field_map:
            return Response(
                {"error": "OCR field map not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            if self.is_commit_request(request):
                rows = self.get_rows(request)
                service = self.image_upload_service_class(
                    user=request.user,
                    upload_service_class=self.upload_service_class,
                    field_map=self.ocr_field_map,
                )
                result = service.save_rows(rows)

                return Response({
                    "message": "Image upload saved",
                    **result
                }, status=status.HTTP_200_OK)

            file = request.FILES.get("file")

            if not file:
                return Response(
                    {"error": "No image uploaded"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            service = self.image_upload_service_class(
                user=request.user,
                upload_service_class=self.upload_service_class,
                field_map=self.ocr_field_map,
                file=file,
            )

            return Response(service.preview(), status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def is_commit_request(self, request):
        value = request.data.get("commit")
        return value is True or str(value).lower() == "true"

    def get_rows(self, request):
        rows = request.data.get("rows", [])

        if isinstance(rows, str):
            rows = json.loads(rows)

        if not isinstance(rows, list):
            raise ValueError("rows must be a list")

        return rows
