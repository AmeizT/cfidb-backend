from django.db import models


class ReportSectionStatus(models.Model):

    class Section(models.TextChoices):
        GENERAL_ATTENDANCE = "general_attendance", "General Attendance"
        SUNDAY_SCHOOL_ATTENDANCE = "sunday_school_attendance", "Sunday School Attendance"
        TITHES = "tithes", "Tithes"
        REVENUE = "revenue", "Revenue"
        OPERATING_EXPENSES = "operating_expenses", "Operating Expenses"
        ACTIVITY_OTHER_EXPENSES = "activity_other_expenses", "Activity & Other Expenses"

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        NO_ACTIVITY = "no_activity", "No activity"
        SKIPPED = "skipped", "Skipped"

    class SkipReason(models.TextChoices):
        RECORDS_UNAVAILABLE = "records_unavailable", "Records unavailable"
        RESPONSIBLE_PERSON_UNAVAILABLE = "responsible_person_unavailable", "Responsible person unavailable"
        TECHNICAL_PROBLEM = "technical_problem", "Technical problem"
        RECORDS_LOST_OR_DAMAGED = "records_lost_or_damaged", "Records lost or damaged"
        ACTIVITY_DID_NOT_TAKE_PLACE = "activity_did_not_take_place", "Activity did not take place"
        INFORMATION_PENDING = "information_pending", "Information pending"
        OTHER = "other", "Other"

    class FollowUpStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CONTACTED = "contacted", "Contacted"
        RESOLVED = "resolved", "Resolved"
        ESCALATED = "escalated", "Escalated"

    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.CASCADE,
        related_name="sections"
    )

    section = models.CharField(
        max_length=50,
        choices=Section.choices
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED
    )

    skip_reason = models.CharField(
        max_length=30,
        choices=SkipReason.choices,
        blank=True,
        null=True
    )

    skip_notes = models.TextField(
        blank=True,
        null=True
    )

    skipped_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skipped_report_sections",
    )
    skipped_at = models.DateTimeField(null=True, blank=True)
    no_activity_confirmed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_no_activity_report_sections",
    )
    no_activity_confirmed_at = models.DateTimeField(null=True, blank=True)
    no_activity_note = models.TextField(blank=True, null=True)
    started_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_report_sections",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_report_sections",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    follow_up_status = models.CharField(
        max_length=20,
        choices=FollowUpStatus.choices,
        default=FollowUpStatus.PENDING,
        db_index=True,
    )
    follow_up_notes = models.TextField(blank=True, null=True)
    follow_up_assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_follow_ups",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("report", "section")


    def clean(self):
        from django.core.exceptions import ValidationError

        if self.status == self.Status.SKIPPED:
            if not self.skip_reason:
                raise ValidationError("A skip reason is required.")

        if self.status == self.Status.NO_ACTIVITY and (
            not self.no_activity_confirmed_by_id or not self.no_activity_confirmed_at
        ):
            raise ValidationError("No activity must record who confirmed it and when.")


    def mark_skipped(self, reason, notes="", user=None):
        from apps.reports.services.section_state_service import update_section_status

        return update_section_status(
            section_obj=self,
            status=self.Status.SKIPPED,
            skip_reason=reason,
            skip_notes=notes,
            updated_by=user,
        )


    def mark_completed(self, user=None):
        from apps.reports.services.section_state_service import update_section_status

        return update_section_status(
            section_obj=self,
            status=self.Status.COMPLETED,
            updated_by=user,
        )


    def mark_not_started(self, user=None):
        from apps.reports.services.section_state_service import update_section_status

        return update_section_status(
            section_obj=self,
            status=self.Status.NOT_STARTED,
            updated_by=user,
        )

    def set_follow_up(self, status, notes=None, assigned_to=None):
        self.follow_up_status = status

        if notes is not None:
            self.follow_up_notes = notes

        if assigned_to is not None:
            self.follow_up_assigned_to = assigned_to

        self.save(update_fields=[
            "follow_up_status",
            "follow_up_notes",
            "follow_up_assigned_to",
            "updated_at",
        ])
