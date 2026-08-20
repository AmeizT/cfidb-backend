from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from decimal import Decimal


class Outreach(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="outreaches",
    )
    title = models.CharField(max_length=255, blank=True)
    outreach_date = models.DateField(db_index=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )

    outreach_team_size = models.PositiveIntegerField(default=0)
    member_attendance = models.PositiveIntegerField(default=0)
    total_people_reached = models.PositiveIntegerField(default=0)
    total_people_converted = models.PositiveIntegerField(default=0)
    total_new_members = models.PositiveIntegerField(default=0)
    total_baptisms = models.PositiveIntegerField(default=0)
    outreach_materials_distributed = models.PositiveIntegerField(default=0)
    outreach_material_notes = models.TextField(blank=True)

    follow_up_required = models.BooleanField(default=False)
    follow_up_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_outreaches",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-outreach_date", "-created_at"]
        indexes = [
            models.Index(fields=["assembly", "outreach_date"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "Outreach"
        verbose_name_plural = "Outreaches"

    def __str__(self):
        title = self.title or "Outreach"
        return f"{self.assembly} - {title} ({self.outreach_date})"


class ChurchMeeting(models.Model):
    class MeetingType(models.TextChoices):
        BOARD = "board", "Board"
        DEACONS = "deacons", "Deacons"
        ELDERS = "elders", "Elders"
        PASTORS = "pastors", "Pastors"
        WORKERS = "workers", "Workers"
        YOUTH = "youth", "Youth"
        PRAYER = "prayer", "Prayer"
        GENERAL = "general", "General"

    class Mode(models.TextChoices):
        IN_PERSON = "in_person", "In Person"
        VIRTUAL = "virtual", "Virtual"
        HYBRID = "hybrid", "Hybrid"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="meetings",
    )
    title = models.CharField(max_length=255)
    meeting_type = models.CharField(
        max_length=30,
        choices=MeetingType.choices,
        default=MeetingType.GENERAL,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )
    mode = models.CharField(
        max_length=20,
        choices=Mode.choices,
        default=Mode.IN_PERSON,
    )
    venue = models.CharField(max_length=255, blank=True)
    online_link = models.URLField(blank=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    chairperson = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="chaired_church_meetings",
        null=True,
        blank=True,
    )
    secretary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="minuted_church_meetings",
        null=True,
        blank=True,
    )
    expected_attendance = models.PositiveIntegerField(default=0)
    actual_attendance = models.PositiveIntegerField(default=0)
    agenda = models.TextField(blank=True)
    minutes_summary = models.TextField(blank=True)
    decisions = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_church_meetings",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "meeting"
        verbose_name_plural = "meetings"
        ordering = ["-starts_at", "-created_at"]
        indexes = [
            models.Index(fields=["assembly", "starts_at"]),
            models.Index(fields=["meeting_type"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.assembly} - {self.title}"


class Forecast(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="forecasts",
    )
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    new_members = models.PositiveIntegerField(default=0)
    tithes_collected = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal(0))
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal(0))
    expense_budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal(0))
    remittance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal(0))

    attendance = models.PositiveIntegerField(default=0)
    average_attendance = models.PositiveIntegerField(default=0)
    first_time_guests = models.PositiveIntegerField(default=0)
    people_reached = models.PositiveIntegerField(default=0)
    people_converted = models.PositiveIntegerField(default=0)
    baptisms = models.PositiveIntegerField(default=0)
    outreaches_conducted = models.PositiveIntegerField(default=0)
    homecells_planted = models.PositiveIntegerField(default=0)
    leaders_trained = models.PositiveIntegerField(default=0)
    meetings_conducted = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_forecasts",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-month", "assembly__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "year", "month"],
                name="unique_assembly_forecast",
            )
        ]
        indexes = [
            models.Index(fields=["assembly", "year", "month"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.assembly} forecast - {self.year}-{self.month:02d}"
