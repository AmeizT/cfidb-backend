import pandas as pd
from decimal import Decimal
from .base_upload import BaseUploadService
from apps.bookkeeper.models import Overhead, OverheadType
from apps.bookkeeper.category_matching import normalize_financial_category_name


class OverheadUploadService(BaseUploadService):
    model_name = "overhead"
    model = Overhead

    def validate_columns(self):
        required = ["timestamp", "overhead_type", "amount"]
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
        timestamp = timestamp.date()

        # -------------------------
        # Amount
        # -------------------------
        amount = row.get("amount")
        if pd.isna(amount):
            raise ValueError("Amount is required")

        amount = Decimal(amount)

        # -------------------------
        # Overhead Type (smart lookup)
        # -------------------------
        type_name = str(row.get("overhead_type", "")).strip()

        if not type_name:
            raise ValueError("overhead_type is required")

        # 1. Assembly-specific
        overhead_type = OverheadType.objects.filter(
            assembly=user_church,
            normalized_name=normalize_financial_category_name(type_name),
        ).first()

        # 2. Global fallback
        if not overhead_type:
            overhead_type = OverheadType.objects.filter(
                is_global=True,
                normalized_name=normalize_financial_category_name(type_name),
            ).first()

        # 3. Create if not found
        if not overhead_type:
            overhead_type = OverheadType.objects.create(
                name=type_name,
                assembly=user_church,
                is_global=False,
                is_required=False,
                is_active=True,
                needs_review=True,
                created_by=self.user,
            )

        return {
            "assembly": user_church,
            "timestamp": timestamp,
            "amount": amount,
            "overhead_type": overhead_type,
            "notes": row.get("notes", "") or "",
        }

    def save_row(self, data):
                
        existing = Overhead.objects.filter(
            assembly=data["assembly"],
            overhead_type=data["overhead_type"],
            timestamp__year=data["timestamp"].year,
            timestamp__month=data["timestamp"].month,
        ).first()

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.save()
            return False  # updated

        obj = Overhead.objects.create(**data)
        return True  # created
