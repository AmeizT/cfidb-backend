import pandas as pd
from decimal import Decimal
from .base_upload import BaseUploadService
from apps.bookkeeper.models import Tithe, PaymentMethod
from apps.people.models import Member


class TitheUploadService(BaseUploadService):
    model_name = "tithe"
    model = Tithe

    def validate_columns(self):
        required = ["timestamp", "amount"]
        for col in required:
            if col not in self.df.columns: # type: ignore
                raise ValueError(f"Missing required column: {col}")

    def transform_row(self, row):
        print("RAW ROW:", row.to_dict())
        user_church = getattr(self.user, "church", None)

        timestamp = pd.to_datetime(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            raise ValueError("Invalid timestamp")
        
        timestamp = timestamp.date()

        amount = row.get("amount")
        if pd.isna(amount):
            raise ValueError("Amount is required")

        amount = Decimal(amount)

        payment_method = str(row.get("payment_method", "Bank")).strip()
        print("Payment method:", payment_method)

        valid_methods = [c[0] for c in PaymentMethod.choices]
        print("Valid methods:", valid_methods)

        if payment_method not in valid_methods:
            raise ValueError(f"Invalid payment_method: {payment_method}")

        member_name = str(row.get("member_name", "")).strip()
        print("Member name:", member_name)

        if not member_name:
            member_obj = None
        else:
            parts = member_name.split()

            if len(parts) < 2:
                raise ValueError(f"Invalid member_name: {member_name}")

            first_name = parts[0]
            last_name = parts[-1]

            matches = Member.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                assembly=user_church
            )

            if matches.count() == 1:
                member_obj = matches.first()
            elif matches.count() > 1:
                raise ValueError(f"Multiple members found: {member_name}")
            else:
                raise ValueError(f"Member not found: {member_name}")

        print("FOUND MEMBER:", member_obj)

        return {
            "assembly": user_church,
            "timestamp": timestamp,
            "amount": amount,
            "payment_method": payment_method,
            "member": member_obj,
            "reference_code": row.get("reference_code", "") or "",
            "notes": row.get("notes", "") or "",
        }

    def save_row(self, data):
        print("SAVING DATA:", data)

        member = data.get("member")

        # -------------------------
        # Anonymous → always create
        # -------------------------
        if member is None:
            print("Anonymous tithe → creating new record")
            obj = Tithe.objects.create(**data)
            print("SAVED:", obj)
            return True

        # -------------------------
        # Deduplicate using report (month)
        # -------------------------
        timestamp = data.get("timestamp")

        month = timestamp.month
        year = timestamp.year

        existing = Tithe.objects.filter(
            assembly=data.get("assembly"),
            member=member,
            timestamp__year=year,
            timestamp__month=month,
        ).first()

        if existing:
            print("UPDATING EXISTING TITHE:", existing)

            for key, value in data.items():
                setattr(existing, key, value)

            existing.save()
            print("UPDATED:", existing)
            return False

        print("CREATING NEW TITHE")
        obj = Tithe.objects.create(**data)
        print("SAVED:", obj)
        return True