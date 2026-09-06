from decimal import Decimal, InvalidOperation

import pandas as pd

from apps.people.choices.services import SundaySchoolClassChoices
from apps.people.models import Member, SundaySchoolAttendance

from .base_upload import BaseUploadService


class SundaySchoolAttendanceUploadService(BaseUploadService):
    model_name = "sunday_school_attendance"
    model = SundaySchoolAttendance

    required_columns = [
        "service_date",
        "class_name",
        "teacher_name",
        "boys",
        "girls",
        "male_visitors",
        "female_visitors",
        "male_first_timers",
        "female_first_timers",
    ]

    def validate_columns(self):
        missing = [
            column for column in self.required_columns
            if column not in self.df.columns
        ]
        if missing:
            raise ValueError(f"Missing required column: {missing[0]}")

    def transform_row(self, row):
        assembly = getattr(self.user, "church", None)
        if assembly is None:
            raise ValueError("An active assembly is required")

        service_date = pd.to_datetime(row.get("service_date"), errors="coerce")
        if pd.isna(service_date):
            raise ValueError("Invalid service_date")

        class_name = str(row.get("class_name", "")).strip().lower()
        class_aliases = {
            str(label).strip().lower(): value
            for value, label in SundaySchoolClassChoices.choices
        }
        class_name = class_aliases.get(class_name, class_name)
        valid_classes = {value for value, _ in SundaySchoolClassChoices.choices}
        if class_name not in valid_classes:
            raise ValueError(f"Invalid class_name: {class_name}")

        teacher = self._resolve_teacher(row.get("teacher_name"), assembly)

        return {
            "assembly": assembly,
            "teacher": teacher,
            "reported_by": self.user,
            "service_date": service_date.date(),
            "class_name": class_name,
            "boys": self._non_negative_integer(row, "boys"),
            "girls": self._non_negative_integer(row, "girls"),
            "male_visitors": self._non_negative_integer(row, "male_visitors"),
            "female_visitors": self._non_negative_integer(row, "female_visitors"),
            "male_first_timers": self._non_negative_integer(row, "male_first_timers"),
            "female_first_timers": self._non_negative_integer(row, "female_first_timers"),
            "lesson_title": self._text(row.get("lesson_title")),
            "scripture_reference": self._text(row.get("scripture_reference")),
            "offering": self._non_negative_decimal(row.get("offering"), "offering"),
            "remarks": self._text(row.get("remarks")),
        }

    def save_row(self, data):
        instance, created = SundaySchoolAttendance.objects.update_or_create(
            assembly=data["assembly"],
            service_date=data["service_date"],
            class_name=data["class_name"],
            is_deleted=False,
            defaults=data,
        )
        return created

    def _resolve_teacher(self, raw_value, assembly):
        teacher_name = self._text(raw_value)
        if not teacher_name:
            raise ValueError("teacher_name is required")

        parts = teacher_name.split()
        if len(parts) < 2:
            raise ValueError(f"Invalid teacher_name: {teacher_name}")

        matches = Member.objects.filter(
            assembly=assembly,
            first_name__iexact=parts[0],
            last_name__iexact=parts[-1],
        )
        if matches.count() == 1:
            return matches.first()
        if matches.count() > 1:
            raise ValueError(f"Multiple teachers found: {teacher_name}")
        raise ValueError(f"Teacher not found: {teacher_name}")

    def _non_negative_integer(self, row, field):
        value = row.get(field)
        if pd.isna(value) or value == "":
            raise ValueError(f"{field} is required")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid {field}") from None
        if number < 0 or number != number.to_integral_value():
            raise ValueError(f"{field} must be a non-negative whole number")
        return int(number)

    def _non_negative_decimal(self, value, field):
        if pd.isna(value) or value == "":
            return Decimal("0")
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid {field}") from None
        if number < 0:
            raise ValueError(f"{field} cannot be negative")
        return number

    def _text(self, value):
        if pd.isna(value):
            return ""
        return str(value).strip()
