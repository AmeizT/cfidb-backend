from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from datetime import date


class AssemblyMembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    ENDED = "ended", "Ended"


class MembershipEndReason(models.TextChoices):
    TRANSFERRED = "transferred", "Transferred"
    RESIGNED = "resigned", "Resigned"
    RELOCATED = "relocated", "Relocated"
    REMOVED = "removed", "Removed"
    DECEASED = "deceased", "Deceased"
    LOST_CONTACT = "lost_contact", "Lost Contact"
    DUPLICATE = "duplicate", "Duplicate Record"
    OTHER = "other", "Other"


class AssemblyMembershipQuerySet(models.QuerySet):
    def current(self):
        return self.filter(
            status__in=[
                AssemblyMembershipStatus.ACTIVE,
                AssemblyMembershipStatus.INACTIVE,
            ]
        )

    def active(self):
        return self.filter(status=AssemblyMembershipStatus.ACTIVE)

    def inactive(self):
        return self.filter(status=AssemblyMembershipStatus.INACTIVE)

    def former(self):
        return self.filter(status=AssemblyMembershipStatus.ENDED)

    def for_assembly(self, assembly):
        if assembly is None:
            return self.none()

        assembly_id = getattr(assembly, "pk", assembly)
        return self.filter(assembly_id=assembly_id)

    def for_member(self, member):
        member_id = getattr(member, "pk", member)
        return self.filter(member_id=member_id)

    def transferred(self):
        return self.former().filter(
            end_reason=MembershipEndReason.TRANSFERRED,
        )

    def resigned(self):
        return self.former().filter(
            end_reason=MembershipEndReason.RESIGNED,
        )

    def deceased(self):
        return self.former().filter(
            end_reason=MembershipEndReason.DECEASED,
        )

    def with_related_data(self):
        return self.select_related(
            "member",
            "assembly",
            "transfer",
            "created_by",
            "updated_by",
        )


class AssemblyMembershipManager(
    models.Manager.from_queryset(AssemblyMembershipQuerySet)
):
    pass


class AssemblyMembership(models.Model):
    """
    Represents a Member's relationship with an assembly.

    A Member may have multiple historical AssemblyMembership records but
    should only have one current membership at a time.
    """

    member = models.ForeignKey(
        "people.Member",
        on_delete=models.CASCADE,
        related_name="assembly_memberships",
    )

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="assembly_memberships",
    )

    status = models.CharField(
        max_length=20,
        choices=AssemblyMembershipStatus.choices,
        default=AssemblyMembershipStatus.ACTIVE,
    )

    joined_on = models.DateField(
        default=timezone.localdate,
    )

    ended_on = models.DateField(
        null=True,
        blank=True,
    )

    end_reason = models.CharField(
        max_length=30,
        choices=MembershipEndReason.choices,
        blank=True,
    )

    end_notes = models.TextField(blank=True)

    transfer = models.ForeignKey(
        "people.MemberTransferRequest",
        on_delete=models.SET_NULL,
        related_name="assembly_membership_changes",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_assembly_memberships",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_assembly_memberships",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AssemblyMembershipManager()
    Status = AssemblyMembershipStatus

    class Meta:
        ordering = ["-joined_on", "-created_at"]
        verbose_name = "Assembly Membership"
        verbose_name_plural = "Assembly Memberships"
        indexes = [
            models.Index(fields=["assembly", "status"]),
            models.Index(fields=["member", "status"]),
            models.Index(fields=["assembly", "ended_on"]),
            models.Index(fields=["assembly", "end_reason"]),
            models.Index(fields=["member", "joined_on"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member"],
                condition=Q(
                    status__in=[
                        AssemblyMembershipStatus.ACTIVE,
                        AssemblyMembershipStatus.INACTIVE,
                    ]
                ),
                name="one_current_assembly_membership_per_member",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=AssemblyMembershipStatus.ENDED,
                        ended_on__isnull=False,
                    )
                    | Q(
                        status__in=[
                            AssemblyMembershipStatus.ACTIVE,
                            AssemblyMembershipStatus.INACTIVE,
                        ],
                        ended_on__isnull=True,
                    )
                ),
                name="assembly_membership_valid_end_date",
            ),
            models.CheckConstraint(
                condition=(
                    Q(ended_on__isnull=True)
                    | Q(ended_on__gte=models.F("joined_on"))
                ),
                name="assembly_membership_ended_after_joining",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(status=AssemblyMembershipStatus.ENDED)
                    | ~Q(end_reason="")
                ),
                name="ended_membership_requires_reason",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(end_reason=MembershipEndReason.TRANSFERRED)
                    | Q(transfer__isnull=False)
                ),
                name="transferred_membership_requires_transfer",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.member} — {self.assembly} "
            f"({self.get_status_display()})"
        )

    @property
    def is_current(self) -> bool:
        return self.status in {
            AssemblyMembershipStatus.ACTIVE,
            AssemblyMembershipStatus.INACTIVE,
        }

    @property
    def is_former(self) -> bool:
        return self.status == AssemblyMembershipStatus.ENDED

    @property
    def start_date(self):
        """Deprecated compatibility alias for ``joined_on``."""
        return self.joined_on

    @property
    def end_date(self):
        """Deprecated compatibility alias for ``ended_on``."""
        return self.ended_on

    def clean(self):
        errors = {}

        if self.status == AssemblyMembershipStatus.ENDED:
            if not self.ended_on:
                errors["ended_on"] = (
                    "An ended membership must have an ending date."
                )

            if not self.end_reason:
                errors["end_reason"] = (
                    "An ended membership must have an ending reason."
                )
        else:
            if self.ended_on:
                errors["ended_on"] = (
                    "A current membership cannot have an ending date."
                )

            if self.end_reason:
                errors["end_reason"] = (
                    "A current membership cannot have an ending reason."
                )

            if self.end_notes:
                errors["end_notes"] = (
                    "A current membership cannot have ending notes."
                )

        if self.ended_on and self.ended_on < self.joined_on:
            errors["ended_on"] = (
                "The membership ending date cannot be before the joining date."
            )

        if (
            self.end_reason == MembershipEndReason.TRANSFERRED
            and not self.transfer_id
        ):
            errors["transfer"] = (
                "A transferred membership should be linked to its transfer."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def mark_inactive(self, *, updated_by=None):
        if self.status == AssemblyMembershipStatus.ENDED:
            raise ValidationError(
                "An ended membership cannot be marked inactive."
            )

        self.status = AssemblyMembershipStatus.INACTIVE
        self.updated_by = updated_by
        self.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        return self

    def mark_active(self, *, updated_by=None):
        if self.status == AssemblyMembershipStatus.ENDED:
            raise ValidationError(
                "An ended membership cannot be reactivated. "
                "Create a new assembly membership instead."
            )

        self.status = AssemblyMembershipStatus.ACTIVE
        self.updated_by = updated_by
        self.save(
            update_fields=[
                "status",
                "updated_by",
                "updated_at",
            ]
        )

        return self

    @transaction.atomic
    def end_membership(
        self,
        *,
        reason: str,
        ended_on: date | None = None,
        notes: str = "",
        transfer=None,
        updated_by=None,
        close_household_membership: bool = True,
        clear_member_assembly: bool = True,
    ):
        """
        End this assembly membership.

        This preserves the Member and the membership history.

        During a transfer, call this method and create the destination
        AssemblyMembership inside the same transaction.
        """
        locked_membership = (
            AssemblyMembership.objects.select_for_update()
            .select_related("member", "assembly")
            .get(pk=self.pk)
        )

        if locked_membership.status == AssemblyMembershipStatus.ENDED:
            return locked_membership

        effective_ended_on = ended_on or timezone.localdate()

        if effective_ended_on < locked_membership.joined_on:
            raise ValidationError(
                {
                    "ended_on": (
                        "The membership ending date cannot be before "
                        "the joining date."
                    )
                }
            )

        if reason == MembershipEndReason.TRANSFERRED and transfer is None:
            raise ValidationError(
                {
                    "transfer": (
                        "A transfer must be supplied when ending a membership "
                        "because the member was transferred."
                    )
                }
            )

        if close_household_membership:
            from .former_members import HouseholdMember

            active_household_memberships = (
                HouseholdMember.objects.select_for_update()
                .filter(
                    member=locked_membership.member,
                    left_on__isnull=True,
                )
            )

            for household_membership in active_household_memberships:
                household_membership.leave(
                    left_on=effective_ended_on,
                    updated_by=updated_by,
                )

        locked_membership.status = AssemblyMembershipStatus.ENDED
        locked_membership.ended_on = effective_ended_on
        locked_membership.end_reason = reason
        locked_membership.end_notes = notes
        locked_membership.transfer = transfer
        locked_membership.updated_by = updated_by

        locked_membership.save(
            update_fields=[
                "status",
                "ended_on",
                "end_reason",
                "end_notes",
                "transfer",
                "updated_by",
                "updated_at",
            ]
        )

        # This assumes Member.assembly is nullable after your model update.
        if (
            clear_member_assembly
            and locked_membership.member.assembly_id
            == locked_membership.assembly_id
        ):
            locked_membership.member.assembly = None
            locked_membership.member.updated_by = updated_by
            locked_membership.member.save(
                update_fields=[
                    "assembly",
                    "updated_by",
                    "updated_at",
                ]
            )

        return locked_membership


# 
