import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q


STUDENT_MODEL = getattr(
    settings,
    "EXAMINATIONS_STUDENT_MODEL",
    settings.AUTH_USER_MODEL,
)


def examination_pdf_upload_path(instance, filename):
    safe_filename = Path(filename).name
    return (
        f"examinations/{instance.examination_id}/imports/"
        f"{uuid.uuid4()}_{safe_filename}"
    )


class ResultStatus(models.TextChoices):
    SCORED = "scored", "Scored"
    ABSENT = "absent", "Absent"
    WITHHELD = "withheld", "Withheld"
    CANCELLED = "cancelled", "Cancelled"




class CBAStudentReference(models.Model):
    source_id = models.PositiveBigIntegerField(unique=True)
    student_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    source_username = models.UUIDField(null=True, blank=True)

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=50, default="student")

    avatar = models.URLField(blank=True)
    avatar_fallback = models.CharField(max_length=32, blank=True)
    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    source_created_at = models.DateTimeField(null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["first_name", "last_name", "student_number"]
        indexes = [
            models.Index(fields=["student_number"]),
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["is_active", "role"]),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self):
        return self.full_name

    def __str__(self):
        return f"{self.student_number} - {self.full_name}"


class Examination(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=255)
    academic_year = models.PositiveSmallIntegerField(null=True, blank=True)
    examination_date = models.DateField(null=True, blank=True)

    total_marks = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=Decimal("100.00"),
    )
    pass_mark = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_examinations",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-academic_year", "name", "-created_at"]
        indexes = [
            models.Index(fields=["academic_year", "name"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_marks__gt=0),
                name="examination_total_marks_gt_zero",
            ),
        ]
        permissions = [
            ("manage_examinations", "Can manage examinations"),
        ]

    def clean(self):
        errors = {}

        if self.total_marks is not None and self.total_marks <= 0:
            errors["total_marks"] = "Total marks must be greater than zero."

        if self.pass_mark is not None:
            if self.pass_mark < 0:
                errors["pass_mark"] = "Pass mark cannot be negative."
            elif (
                self.total_marks is not None
                and self.pass_mark > self.total_marks
            ):
                errors["pass_mark"] = (
                    "Pass mark cannot be greater than total marks."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        if self.academic_year:
            return f"{self.academic_year} - {self.name}"
        return self.name


class ExaminationImport(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        REVIEW_REQUIRED = "review_required", "Review required"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="imports",
    )

    pdf_file = models.FileField(
        upload_to=examination_pdf_upload_path,
        validators=[FileExtensionValidator(["pdf"])],
    )
    original_filename = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    total_rows = models.PositiveIntegerField(default=0)
    matched_rows = models.PositiveIntegerField(default=0)
    unmatched_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    excluded_rows = models.PositiveIntegerField(default=0)

    parser_version = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="examination_imports",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["examination", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.examination} - {self.original_filename}"


class ExaminationImportRow(models.Model):
    class MatchStatus(models.TextChoices):
        MATCHED = "matched", "Matched"
        UNMATCHED = "unmatched", "Student not found"
        DUPLICATE = "duplicate", "Duplicate"
        INVALID = "invalid", "Invalid"
        EXCLUDED = "excluded", "Excluded"

    import_batch = models.ForeignKey(
        ExaminationImport,
        on_delete=models.CASCADE,
        related_name="rows",
    )

    row_number = models.PositiveIntegerField(null=True, blank=True)

    raw_student_number = models.CharField(max_length=100)
    normalized_student_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )

    raw_result = models.CharField(max_length=255)
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    result_status = models.CharField(
        max_length=20,
        choices=ResultStatus.choices,
        null=True,
        blank=True,
    )

    matched_student = models.ForeignKey(
        STUDENT_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="matched_examination_import_rows",
    )

    match_status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.UNMATCHED,
    )
    validation_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["row_number", "id"]
        indexes = [
            models.Index(fields=["import_batch", "match_status"]),
            models.Index(
                fields=["import_batch", "normalized_student_number"]
            ),
        ]

    def clean(self):
        errors = {}

        if self.match_status == self.MatchStatus.MATCHED:
            if self.matched_student_id is None:
                errors["matched_student"] = (
                    "A matched row must have a student."
                )

        if self.result_status == ResultStatus.SCORED:
            if self.score is None:
                errors["score"] = "A scored row must have a score."
            elif self.score < 0:
                errors["score"] = "Score cannot be negative."
            elif (
                self.import_batch_id
                and self.score > self.import_batch.examination.total_marks
            ):
                errors["score"] = (
                    "Score cannot exceed the examination total marks."
                )
        elif self.result_status in {
            ResultStatus.ABSENT,
            ResultStatus.WITHHELD,
            ResultStatus.CANCELLED,
        }:
            if self.score is not None:
                errors["score"] = (
                    "Absent, withheld, or cancelled rows cannot have a score."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        student_number = (
            self.normalized_student_number or self.raw_student_number
        )
        return f"{student_number} - {self.raw_result}"


class ExaminationResult(models.Model):
    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="results",
    )

    student = models.ForeignKey(
        STUDENT_MODEL,
        on_delete=models.PROTECT,
        related_name="examination_results",
    )

    student_number_snapshot = models.CharField(
        max_length=100,
        db_index=True,
    )

    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=ResultStatus.choices,
        default=ResultStatus.SCORED,
    )

    raw_imported_value = models.CharField(max_length=255, blank=True)

    source_import = models.ForeignKey(
        ExaminationImport,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_results",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["student_number_snapshot"]
        indexes = [
            models.Index(fields=["examination", "status"]),
            models.Index(fields=["student", "examination"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["examination", "student"],
                name="unique_student_result_per_examination",
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | Q(score__gte=0),
                name="examination_result_score_not_negative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=ResultStatus.SCORED,
                        score__isnull=False,
                    )
                    | Q(
                        status__in=[
                            ResultStatus.ABSENT,
                            ResultStatus.WITHHELD,
                            ResultStatus.CANCELLED,
                        ],
                        score__isnull=True,
                    )
                ),
                name="examination_result_status_matches_score",
            ),
        ]

    def clean(self):
        errors = {}

        if self.status == ResultStatus.SCORED:
            if self.score is None:
                errors["score"] = "A scored result must have a score."
            elif self.score < 0:
                errors["score"] = "Score cannot be negative."
            elif (
                self.examination_id
                and self.score > self.examination.total_marks
            ):
                errors["score"] = (
                    "Score cannot exceed the examination total marks."
                )
        elif self.score is not None:
            errors["score"] = (
                "Absent, withheld, or cancelled results cannot have a score."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def percentage(self):
        if (
            self.status != ResultStatus.SCORED
            or self.score is None
            or not self.examination.total_marks
        ):
            return None

        return (
            self.score / self.examination.total_marks
        ) * Decimal("100")

    @property
    def passed(self):
        if (
            self.status != ResultStatus.SCORED
            or self.score is None
            or self.examination.pass_mark is None
        ):
            return None

        return self.score >= self.examination.pass_mark

    def __str__(self):
        return (
            f"{self.student_number_snapshot} - "
            f"{self.examination.name}"
        )
