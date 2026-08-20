import pandas as pd
from decimal import Decimal
from .base_upload import BaseUploadService
from apps.bookkeeper.models import Expenditure


class ExpenditureUploadService(BaseUploadService):
    model_name = "expenditure"
    model = Expenditure

    def validate_columns(self):
        required = ["invoice_date", "name", "category", "quantity", "price"]
        for col in required:
            if col not in self.df.columns: # type: ignore
                raise ValueError(f"Missing required column: {col}")

    def transform_row(self, row):
        user_church = getattr(self.user, "church", None)

        # -------------------------
        # Date
        # -------------------------
        invoice_date = pd.to_datetime(row.get("invoice_date"), errors="coerce")
        if pd.isna(invoice_date):
            raise ValueError("Invalid invoice_date")
        invoice_date = invoice_date.date()

        # -------------------------
        # Category validation
        # -------------------------
        category = str(row.get("category", "")).lower().strip()
        valid_categories = [c[0] for c in Expenditure.EXPENSE_TYPE_CHOICES]

        if category not in valid_categories:
            raise ValueError(f"Invalid category: {category}")

        # -------------------------
        # Helpers
        # -------------------------
        def get_int(field):
            val = row.get(field, 0)
            return int(val) if pd.notna(val) else 0

        def get_decimal(field):
            val = row.get(field, 0)
            return Decimal(val) if pd.notna(val) else Decimal("0.00")

        # -------------------------
        # Optional fields
        # -------------------------
        invoice_number = row.get("invoice_number") or ""
        supplier = row.get("supplier") or ""
        description = row.get("description") or ""

        return {
            "assembly": user_church,
            "invoice_date": invoice_date,
            "invoice_number": invoice_number,
            "name": row.get("name", ""),
            "description": description,
            "category": category,
            "supplier": supplier,
            "quantity": get_int("quantity"),
            "price": get_decimal("price"),
        }

    def save_row(self, data):
        obj, created = Expenditure.objects.update_or_create(
            assembly=data["assembly"],
            invoice_date=data["invoice_date"],
            name=data["name"],
            defaults=data
        )
        return created