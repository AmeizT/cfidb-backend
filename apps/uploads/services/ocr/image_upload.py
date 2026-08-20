import os

from .field_mapper import FieldMapper
from .image_preprocessor import ImagePreprocessor
from .ocr_engine import PaddleOcrEngine
from .parser import OcrReportParser


class OcrImageUploadService:
    def __init__(
        self,
        user,
        upload_service_class,
        field_map,
        file=None,
        ocr_engine=None,
        preprocessor=None,
    ):
        self.user = user
        self.file = file
        self.upload_service_class = upload_service_class
        self.field_map = field_map
        self.preprocessor = preprocessor or ImagePreprocessor()
        self.ocr_engine = ocr_engine

    def preview(self):
        if not self.file:
            raise ValueError("No image uploaded")

        cleaned_image_path = None

        try:
            cleaned_image_path = self.preprocessor.preprocess(self.file)
            extraction = self.get_ocr_engine().extract_text(cleaned_image_path)
            parsed = self.parse_extraction(extraction)
            validation = self.validate_rows(parsed["rows"])

            return {
                "success": len(validation["errors"]) == 0,
                "raw_text": extraction["raw_text"],
                "text_lines": extraction["text_lines"],
                "bounding_boxes": extraction["bounding_boxes"],
                "detections": extraction["detections"],
                "confidence": extraction["confidence"],
                "preview": validation["preview"],
                "errors": validation["errors"],
                "warnings": parsed["warnings"],
            }
        finally:
            if cleaned_image_path and os.path.exists(cleaned_image_path):
                os.unlink(cleaned_image_path)

    def save_rows(self, rows):
        if not rows:
            raise ValueError("No rows supplied for upload")

        upload_service = self.build_upload_service()
        return upload_service.process_rows(rows)

    def parse_extraction(self, extraction):
        mapper = FieldMapper(self.field_map)
        parser = OcrReportParser(mapper)
        parsed = parser.parse(
            raw_text=extraction["raw_text"],
            text_lines=extraction["text_lines"],
            detections=extraction.get("detections"),
        )
        parsed["rows"] = [
            self.ensure_configured_fields(row)
            for row in parsed["rows"]
        ]
        return parsed

    def ensure_configured_fields(self, row):
        next_row = {
            field: row.get(field, "")
            for field in self.field_map.keys()
        }

        for field, value in row.items():
            if field not in next_row:
                next_row[field] = value

        return next_row

    def validate_rows(self, rows):
        if not rows:
            return {
                "preview": [],
                "errors": [{
                    "row": 1,
                    "field": "",
                    "message": (
                        "No structured rows were found in the OCR text. "
                        "Check that the image uses a supported report template."
                    ),
                }],
            }

        upload_service = self.build_upload_service()
        return upload_service.preview_rows(rows)

    def build_upload_service(self):
        return self.upload_service_class(
            user=self.user,
            file=self.file,
        )

    def get_ocr_engine(self):
        if self.ocr_engine is None:
            self.ocr_engine = PaddleOcrEngine()

        return self.ocr_engine
