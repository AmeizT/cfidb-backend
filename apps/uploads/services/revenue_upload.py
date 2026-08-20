import pandas as pd
from decimal import Decimal
from .base_upload import BaseUploadService
from apps.bookkeeper.models import Revenue, RevenueCategory
from apps.bookkeeper.category_matching import normalize_financial_category_name


class RevenueUploadService(BaseUploadService):
    model_name = "revenue"
    model = Revenue

    def validate_columns(self):
        required = ["timestamp", "category", "amount"]
        for col in required:
            if col not in self.df.columns: # type: ignore
                raise ValueError(f"Missing required column: {col}")

    def transform_row(self, row):
        user_church = getattr(self.user, "church", None)

        # -------------------------
        # Timestamp
        # -------------------------
        timestamp = pd.to_datetime(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            raise ValueError("Invalid timestamp")
        timestamp = timestamp.date()  # convert to datetime.date

        # -------------------------
        # Amount
        # -------------------------
        amount = row.get("amount")
        if pd.isna(amount):
            raise ValueError("Amount is required")

        amount = Decimal(amount)

        # -------------------------
        # Category (Auto-create)
        # -------------------------
        category_name = str(row.get("category", "")).strip()

        if not category_name:
            raise ValueError("Category is required")

        # category_obj, _ = RevenueCategory.objects.get_or_create(
        #     assembly=user_church,
        #     name__iexact=category_name,
        #     defaults={
        #         "name": category_name,
        #         "is_standard": False,
        #         "is_active": True,
        #     }
        # )

        category_obj = RevenueCategory.objects.filter(
            assembly=user_church,
            normalized_name=normalize_financial_category_name(category_name),
        ).first()

        if not category_obj:
            category_obj = RevenueCategory.objects.create(
                assembly=user_church,
                name=category_name,
                is_standard=False,
                is_active=True,
                needs_review=True,
                created_by=self.user,
            )

        return {
            "assembly": user_church,
            "timestamp": timestamp,
            "amount": amount,
            "category": category_obj,
            "notes": row.get("notes", "") or "",
        }

    def save_row(self, data):
        obj, created = Revenue.objects.update_or_create(
            assembly=data["assembly"],
            timestamp=data["timestamp"],
            category=data["category"],
            defaults=data
        )
        print("Saved:", obj, "Created:", created)
        return created
