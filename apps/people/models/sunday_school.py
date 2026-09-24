from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.people.choices.services import SundaySchoolClassChoices
from apps.reports.mixins import AuditLogMixin
from apps.people.constants import SUNDAY_SCHOOL_START_DATE
from apps.shared.mixins.soft_delete import SoftDeleteManager


class SundaySchoolAttendance(AuditLogMixin, models.Model):
    AUDIT_TRANSACTION_TYPE = "Sunday School Attendance"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE,
        related_name="sunday_school_attendances",
        db_index=True,
    )
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,
        related_name="sunday_school_attendance_set",
        null=True,
        blank=True,
    )
    teacher = models.ForeignKey(
        "people.Member",
        on_delete=models.PROTECT,
        related_name="sunday_school_attendances",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reported_sunday_school_attendances",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_sunday_school_attendances",
        null=True,
        blank=True,
    )

    service_date = models.DateField(db_index=True)
    class_name = models.CharField(
        max_length=30,
        choices=SundaySchoolClassChoices.choices,
        db_index=True,
    )

    boys = models.PositiveIntegerField(default=0)
    girls = models.PositiveIntegerField(default=0)
    male_visitors = models.PositiveIntegerField(default=0)
    female_visitors = models.PositiveIntegerField(default=0)
    male_first_timers = models.PositiveIntegerField(default=0)
    female_first_timers = models.PositiveIntegerField(default=0)

    lesson_title = models.CharField(max_length=255, blank=True)
    scripture_reference = models.CharField(max_length=120, blank=True)
    offering = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0))
    remarks = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    COUNT_FIELDS = [
        "boys",
        "girls",
        "male_visitors",
        "female_visitors",
        "male_first_timers",
        "female_first_timers",
    ]

    class Meta:
        ordering = ["-service_date", "class_name"]
        verbose_name = "Sunday School Attendance"
        verbose_name_plural = "Sunday School Attendance"
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "class_name", "service_date"],
                condition=models.Q(is_deleted=False),
                name="unique_active_sunday_school_attendance",
            )
        ]
        indexes = [
            models.Index(fields=["assembly", "service_date"]),
            models.Index(fields=["assembly", "status"]),
            models.Index(fields=["teacher", "service_date"]),
        ]

    def __str__(self):
        class_label = self.get_class_name_display() # type: ignore
        return f"{self.service_date} - {self.assembly} - {class_label}"

    @property
    def total_children(self):
        return self.boys + self.girls

    @property
    def total_visitors(self):
        return self.male_visitors + self.female_visitors

    @property
    def total_first_timers(self):
        return self.male_first_timers + self.female_first_timers

    @property
    def grand_total(self):
        return self.total_children + self.total_visitors + self.total_first_timers

    def clean(self):
        errors = {}

        if self.service_date and self.service_date < SUNDAY_SCHOOL_START_DATE:
            errors["service_date"] = (
                f"Sunday School attendance starts on {SUNDAY_SCHOOL_START_DATE.isoformat()}."
            )

        for field in self.COUNT_FIELDS:
            value = getattr(self, field)
            if value is not None and value < 0:
                errors[field] = "Attendance counts cannot be negative."

        if self.offering is not None and self.offering < Decimal("0"):
            errors["offering"] = "Offering cannot be negative."

        if self.teacher_id and self.assembly_id: # type: ignore
            teacher_assembly_id = self.teacher.assembly_id
            if teacher_assembly_id != self.assembly_id: # type: ignore
                errors["teacher"] = "Teacher must belong to the selected assembly."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        from apps.reports.models import AssemblyReport
        from apps.reports.services.lifecycle import ensure_report, report_is_open

        self.full_clean()
        report = self.report
        if report is None:
            report = ensure_report(
                assembly=self.assembly,
                period_start=self.service_date,
                actor=self.reported_by,
            )
            self.report = report
        if report.assembly_id != self.assembly_id or not (
            report.period_start <= self.service_date <= report.period_end
        ):
            raise ValidationError("Sunday School report must match its assembly and service month.")
        if not report_is_open(report):
            raise ValidationError(
                "Start an amendment before changing source records in a submitted report."
            )
        if self.status == self.Status.SUBMITTED and self.submitted_at is None:
            self.submitted_at = timezone.now()

        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"report"}

        super().save(*args, **kwargs)
        self.recalculate_attendance_report()

    def recalculate_attendance_report(self):
        from apps.reports.models import AssemblyReport

        if self.report_id:
            self.report.recalculate_attendance_totals()

    def submit(self, user=None):
        self.status = self.Status.SUBMITTED
        self.reported_by = user or self.reported_by
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "reported_by", "submitted_at", "updated_at"])

    def mark_under_review(self, user=None):
        self.status = self.Status.UNDER_REVIEW
        self.reviewed_by = user or self.reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    def approve(self, user=None):
        self.status = self.Status.APPROVED
        self.reviewed_by = user or self.reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

    def reject(self, user=None):
        self.status = self.Status.REJECTED
        self.reviewed_by = user or self.reviewed_by
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
