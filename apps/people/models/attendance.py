from django.db import models
from apps.reports.models import AuditLog
from apps.reports.mixins import AuditLogMixin
from apps.reports.models import AssemblyReport
from apps.people.choices.weather import WeatherCondition
from apps.people.choices.services import AttendanceCategories
from apps.shared.mixins.soft_delete import SoftDeleteManager


class Attendance(AuditLogMixin, models.Model):
    AUDIT_TRANSACTION_TYPE = "Attendance"

    class CollectionSchema(models.TextChoices):
        LEGACY = "legacy", "Historical totals (gender not collected)"
        GENDER_SPLIT = "gender_split", "Gender-split collection"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE,
        related_name="attendances",
        db_index=True
    )

    report = models.ForeignKey(
        AssemblyReport,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendance_set"
    )

    homecell = models.ForeignKey(
        "people.Homecell",
        on_delete=models.SET_NULL,
        related_name="attendances",
        null=True,
        blank=True
    )

    service_type = models.CharField(
        max_length=24,
        choices=AttendanceCategories.choices,
        default=AttendanceCategories.SUNDAY,
        db_index=True
    )

    is_special_event = models.BooleanField(default=False)
    special_event_name = models.CharField(max_length=255, blank=True)
    weather = models.CharField(
        max_length=30,
        choices=WeatherCondition.choices,
        null=True,
        blank=True,
        db_index=True
    )
    preacher = models.CharField(max_length=255, blank=True)
    sermon = models.TextField(blank=True)
    scriptures = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Numeric metrics
    adults = models.PositiveIntegerField(default=0)
    children = models.PositiveIntegerField(default=0)
    guest_attendance = models.PositiveIntegerField(default=0)
    new_converts = models.PositiveIntegerField(default=0)
    altar_call = models.PositiveIntegerField(default=0)
    baptisms = models.PositiveIntegerField(default=0)

    collection_schema = models.CharField(
        max_length=20,
        choices=CollectionSchema.choices,
        default=CollectionSchema.GENDER_SPLIT,
        db_index=True,
    )
    men = models.PositiveIntegerField(default=0, null=True, blank=True)
    women = models.PositiveIntegerField(default=0, null=True, blank=True)
    visitor_men = models.PositiveIntegerField(default=0, null=True, blank=True)
    visitor_women = models.PositiveIntegerField(default=0, null=True, blank=True)
    new_convert_men = models.PositiveIntegerField(default=0, null=True, blank=True)
    new_convert_women = models.PositiveIntegerField(default=0, null=True, blank=True)
    altar_call_men = models.PositiveIntegerField(default=0, null=True, blank=True)
    altar_call_women = models.PositiveIntegerField(default=0, null=True, blank=True)
    baptism_men = models.PositiveIntegerField(default=0, null=True, blank=True)
    baptism_women = models.PositiveIntegerField(default=0, null=True, blank=True)
    total_adults = models.PositiveIntegerField(default=0, db_index=True)
    total_visitors = models.PositiveIntegerField(default=0, db_index=True)
    total_new_converts = models.PositiveIntegerField(default=0, db_index=True)
    total_altar_call = models.PositiveIntegerField(default=0, db_index=True)
    total_baptisms = models.PositiveIntegerField(default=0, db_index=True)

    online_viewers = models.PositiveIntegerField(default=0)
    volunteers_on_duty = models.PositiveIntegerField(default=0)
    total_leaders_present = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False, db_index=True)

    timestamp = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    NUMERIC_FIELDS = [
        "adults",
        "children",
        "guest_attendance",
        "new_converts",
        "baptisms",
        "altar_call",
        "men",
        "women",
        "visitor_men",
        "visitor_women",
        "new_convert_men",
        "new_convert_women",
        "altar_call_men",
        "altar_call_women",
        "baptism_men",
        "baptism_women",
        "total_adults",
        "total_visitors",
        "total_new_converts",
        "total_altar_call",
        "total_baptisms",
        "online_viewers",
        "volunteers_on_duty",
        "total_leaders_present",
    ]

    class Meta:
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "timestamp", "service_type", "homecell"],
                condition=models.Q(is_deleted=False),
                name="unique_service_attendance"
            )
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.assembly.name} - {self.service_type}"

    @property
    def headcount(self):
        from apps.people.services.attendance_totals import attendance_headcount

        return attendance_headcount(self)

    def recalculate_totals(self):
        if self.collection_schema == self.CollectionSchema.LEGACY:
            self.total_adults = self.adults
            self.total_visitors = self.guest_attendance
            self.total_new_converts = self.new_converts
            self.total_altar_call = self.altar_call
            self.total_baptisms = self.baptisms
            return
        self.total_adults = (self.men or 0) + (self.women or 0)
        self.total_visitors = (self.visitor_men or 0) + (self.visitor_women or 0)
        self.total_new_converts = (self.new_convert_men or 0) + (self.new_convert_women or 0)
        self.total_altar_call = (self.altar_call_men or 0) + (self.altar_call_women or 0)
        self.total_baptisms = (self.baptism_men or 0) + (self.baptism_women or 0)

    def numeric_fields_changed(self):
        if not self.pk:
            return True
        old = Attendance.all_objects.get(pk=self.pk)
        return any(getattr(old, f) != getattr(self, f) for f in self.NUMERIC_FIELDS)

    def assign_report(self):
        if self.report:
            return
        from apps.reports.services.lifecycle import ensure_report

        self.report = ensure_report(assembly=self.assembly, period_start=self.timestamp)

    def save(self, *args, **kwargs):
        is_create = not self.pk
        self.recalculate_totals()
        numeric_changed = self.numeric_fields_changed()

        had_report = bool(self.report_id)
        self.assign_report()

        from apps.reports.services.lifecycle import report_is_open

        if self.report and not report_is_open(self.report):
            from django.core.exceptions import ValidationError
            raise ValidationError("Start an amendment before changing source records in a submitted report.")

        if kwargs.get("update_fields") is not None:
            update_fields = set(kwargs["update_fields"]) | {
                "total_adults",
                "total_visitors",
                "total_new_converts",
                "total_altar_call",
                "total_baptisms",
            }
            if not had_report and self.report_id:
                update_fields.add("report")
            kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

        if numeric_changed and self.report:
            self.report.recalculate_attendance_totals()
            zone_report = getattr(self.report, "zone_report", None)
            if zone_report:
                zone_report.recalculate_from_assemblies()

        if hasattr(self, "log_audit"):
            self.log_audit(
                user=getattr(self, "_current_user", None),
                action=AuditLog.Action.CREATE if is_create else AuditLog.Action.UPDATE
            )
