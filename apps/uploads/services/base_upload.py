import pandas as pd
from django.db import transaction
from apps.uploads.models import UploadError, UploadSession
import logging
from decimal import Decimal
from datetime import date, datetime

logger = logging.getLogger(__name__)


class BaseUploadService:
    model_name = None  # override
    model = None       # override

    def __init__(self, user, file=None):
        self.user = user
        self.file = file

        self.session = None
        self.df = None

        self.created = 0
        self.updated = 0
        self.errors = []

    # -------------------------
    # 🚀 Entry Point
    # -------------------------
    def process(self):
        self.create_session()
        try:
            self.read_file()
            self.validate_columns()
        except Exception:
            self.fail_session()
            raise

        with transaction.atomic():
            for index, row in self.df.iterrows(): # type: ignore
                self.process_row_safe(index, row)

        self.finalize_session()

        return {
            "created": self.created,
            "updated": self.updated,
            "errors": self.errors,
            "session_id": self.session.id # type: ignore
        }

    def process_rows(self, rows):
        self.create_session()

        try:
            self.load_rows(rows)
            self.validate_columns()
        except Exception:
            self.fail_session()
            raise

        with transaction.atomic():
            for index, row in self.df.iterrows(): # type: ignore
                self.process_row_safe(index, row)

        self.finalize_session()

        return {
            "created": self.created,
            "updated": self.updated,
            "errors": self.errors,
            "session_id": self.session.id # type: ignore
        }

    def preview_rows(self, rows):
        self.load_rows(rows)
        preview = self.df.where(pd.notna(self.df), "").to_dict("records") # type: ignore
        errors = []

        try:
            self.validate_columns()
        except Exception as e:
            errors.append({
                "row": 1,
                "field": "columns",
                "message": str(e),
            })
            return {
                "preview": self.serialize_records(preview),
                "errors": errors,
            }

        for index, row in self.df.iterrows(): # type: ignore
            try:
                with transaction.atomic():
                    self.transform_row(row)
                    transaction.set_rollback(True)
            except Exception as e:
                errors.append({
                    "row": int(index) + 2,
                    "field": "",
                    "message": str(e),
                })

        return {
            "preview": self.serialize_records(preview),
            "errors": errors,
        }

    # -------------------------
    # 📦 Session
    # -------------------------
    def create_session(self):
        self.session = UploadSession.objects.create(
            user=self.user,
            model_name=self.model_name,
            file=self.file or "",
            status="processing"
        )

    def fail_session(self):
        if self.session:
            self.session.status = "failed"
            self.session.save()

    def finalize_session(self):
        self.session.success_count = self.created + self.updated # type: ignore
        self.session.error_count = len(self.errors) # type: ignore
        self.session.status = "completed" # type: ignore
        self.session.save() # type: ignore

    # -------------------------
    # 📄 File Handling
    # -------------------------
    def read_file(self):
        try:
            self.df = pd.read_excel(self.file)
            self.normalize_dataframe()

            self.session.total_rows = len(self.df) # type: ignore
            self.session.save() # type: ignore

        except Exception:
            raise ValueError("Invalid Excel file")

    def load_rows(self, rows):
        self.df = pd.DataFrame(rows or [])
        self.normalize_dataframe()

        if self.session:
            self.session.total_rows = len(self.df)
            self.session.save()

    def normalize_dataframe(self):
        self.df.columns = [str(col).strip().lower() for col in self.df.columns] # type: ignore

    def serialize_records(self, records):
        return [
            {key: self.serialize_value(value) for key, value in row.items()}
            for row in records
        ]

    def serialize_value(self, value):
        if isinstance(value, (list, tuple)):
            return [self.serialize_value(item) for item in value]

        if isinstance(value, dict):
            return {
                key: self.serialize_value(item)
                for key, item in value.items()
            }

        if pd.isna(value):
            return ""

        if isinstance(value, Decimal):
            return str(value)

        if isinstance(value, (date, datetime)):
            return value.isoformat()

        return value

    # -------------------------
    # 🧪 Validation Hooks
    # -------------------------
    def validate_columns(self):
        """Override in child"""
        pass

    def transform_row(self, row):
        """Override in child"""
        return row

    def save_row(self, data):
        """Override in child"""
        if data.get("assembly") is None:
            raise ValueError("Missing required field 'assembly'")
        instance, created = self.model.objects.update_or_create( # type: ignore
            assembly=data["assembly"],
            defaults=data
        )
        instance.save()
        return created

    # -------------------------
    # 🔁 Row Processing
    # -------------------------
    def process_row_safe(self, index, row):
        try:
            logger.debug(f"Processing row {index + 2}: {row.to_dict()}")
            data = self.transform_row(row)
            logger.debug(f"Transformed data: {data}")
            created_flag = self.save_row(data)
            print(f"Row {index + 2} created_flag: {created_flag}")

            if created_flag:
                self.created += 1
            else:
                self.updated += 1

        except Exception as e:
            self.handle_error(index, row, e)

    # -------------------------
    # ❌ Error Handling
    # -------------------------
    def handle_error(self, index, row, error):
        UploadError.objects.create(
            session=self.session,
            row_number=int(index) + 2,
            error_message=str(error),
            raw_data=row.to_dict()
        )

        self.errors.append({
            "row": int(index) + 2,
            "error": str(error)
        })
