from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Q
from django.utils import timezone

from .assembly_membership import (
    AssemblyMembership,
    AssemblyMembershipQuerySet,
    AssemblyMembershipStatus,
    MembershipEndReason,
)

# Import Church if it is in another application.
# from churches.models import Church

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


def generate_household_key() -> str:
    """
    Generate a readable, non-sequential household identifier.

    Example:
        HH-A81D52A92B0942F1
    """
    return f"HH-{uuid.uuid4().hex[:16].upper()}"


class HouseholdStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    CLOSED = "closed", "Closed"


class HouseholdRole(models.TextChoices):
    HEAD = "head", "Head of Household"
    SPOUSE = "spouse", "Spouse"
    ADULT = "adult", "Adult"
    CHILD = "child", "Child"
    DEPENDENT = "dependent", "Dependent"
    RELATIVE = "relative", "Relative"
    OTHER = "other", "Other"


# ---------------------------------------------------------------------------
# HOUSEHOLDS
# ---------------------------------------------------------------------------


class HouseholdQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=HouseholdStatus.ACTIVE)

    def inactive(self):
        return self.filter(status=HouseholdStatus.INACTIVE)

    def closed(self):
        return self.filter(status=HouseholdStatus.CLOSED)

    def for_assembly(self, assembly):
        if assembly is None:
            return self.none()

        assembly_id = getattr(assembly, "pk", assembly)
        return self.filter(assembly_id=assembly_id)

    def with_member_counts(self):
        return self.annotate(
            active_member_count=Count(
                "household_memberships",
                filter=Q(
                    household_memberships__left_on__isnull=True,
                    household_memberships__member__is_trash=False,
                ),
                distinct=True,
            ),
            adult_count=Count(
                "household_memberships",
                filter=Q(
                    household_memberships__left_on__isnull=True,
                    household_memberships__member__is_trash=False,
                    household_memberships__role__in=[
                        HouseholdRole.HEAD,
                        HouseholdRole.SPOUSE,
                        HouseholdRole.ADULT,
                        HouseholdRole.RELATIVE,
                    ],
                ),
                distinct=True,
            ),
            minor_count=Count(
                "household_memberships",
                filter=Q(
                    household_memberships__left_on__isnull=True,
                    household_memberships__member__is_trash=False,
                    household_memberships__role__in=[
                        HouseholdRole.CHILD,
                        HouseholdRole.DEPENDENT,
                    ],
                ),
                distinct=True,
            ),
        )


class HouseholdManager(models.Manager.from_queryset(HouseholdQuerySet)):
    pass


class Household(models.Model):
    """
    Represents a family or residential unit within an assembly.

    A Household does not replace a Member's personal contact details.
    It provides shared contact and address information.
    """

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.PROTECT,
        related_name="households",
    )

    household_key = models.CharField(
        max_length=21,
        unique=True,
        editable=False,
        default=generate_household_key,
    )

    name = models.CharField(
        max_length=255,
        help_text="For example: Zhuwao Household",
    )

    status = models.CharField(
        max_length=20,
        choices=HouseholdStatus.choices,
        default=HouseholdStatus.ACTIVE,
    )

    phone_number = models.CharField(
        max_length=17,
        blank=True,
    )

    secondary_phone_number = models.CharField(
        max_length=17,
        blank=True,
    )

    email = models.EmailField(blank=True)

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    address_line2 = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=255,
        blank=True,
    )

    province = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=255,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_households",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_households",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HouseholdManager()

    class Meta:
        ordering = ["name", "household_key"]
        verbose_name = "Household"
        verbose_name_plural = "Households"
        indexes = [
            models.Index(fields=["assembly", "status"]),
            models.Index(fields=["assembly", "name"]),
            models.Index(fields=["household_key"]),
            models.Index(fields=["phone_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.household_key}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        self.name = self.name.strip()

        if not self.name:
            errors["name"] = "A household name is required."

        if self.pk and self.status == HouseholdStatus.CLOSED:
            has_active_members = self.household_memberships.filter(
                left_on__isnull=True,
            ).exists()

            if has_active_members:
                errors["status"] = (
                    "A household cannot be closed while it still has active members."
                )

        if self.pk and self.household_memberships.filter(
            left_on__isnull=True,
        ).exclude(member__assembly_id=self.assembly_id).exists():
            errors["assembly"] = (
                "A household cannot move assemblies while it has members from another assembly."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def primary_contact_membership(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {})

        if "household_memberships" in prefetched:
            return next(
                (
                    membership
                    for membership in prefetched["household_memberships"]
                    if membership.left_on is None
                    and not membership.member.is_trash
                    and membership.is_primary_contact
                ),
                None,
            )

        return (
            self.household_memberships.filter(
                left_on__isnull=True,
                is_primary_contact=True,
                member__is_trash=False,
            )
            .select_related("member")
            .first()
        )

    @property
    def primary_contact(self):
        membership = self.primary_contact_membership
        return membership.member if membership else None

    @property
    def active_members_count(self) -> int:
        annotated_count = getattr(self, "active_member_count", None)

        if annotated_count is not None:
            return annotated_count

        return self.household_memberships.filter(
            left_on__isnull=True,
            member__is_trash=False,
        ).count()

    def add_member(
        self,
        *,
        member,
        role: str = HouseholdRole.OTHER,
        is_primary_contact: bool = False,
        joined_on: date | None = None,
        notes: str = "",
        created_by=None,
    ):
        """
        Add a member to this household.

        The database constraint prevents a member from being active in more
        than one household at the same time.
        """
        return HouseholdMember.objects.create(
            household=self,
            member=member,
            role=role,
            is_primary_contact=is_primary_contact,
            joined_on=joined_on or timezone.localdate(),
            notes=notes,
            created_by=created_by,
        )

    def close(self, *, updated_by=None):
        """
        Close an empty household.

        Active household memberships must be ended first.
        """
        if self.household_memberships.filter(left_on__isnull=True).exists():
            raise ValidationError(
                "End all active household memberships before closing the household."
            )

        self.status = HouseholdStatus.CLOSED
        self.updated_by = updated_by
        self.save(update_fields=["status", "updated_by", "updated_at"])


class HouseholdMemberQuerySet(models.QuerySet):
    def active(self):
        return self.filter(left_on__isnull=True)

    def historical(self):
        return self.filter(left_on__isnull=False)

    def for_household(self, household):
        household_id = getattr(household, "pk", household)
        return self.filter(household_id=household_id)

    def for_member(self, member):
        member_id = getattr(member, "pk", member)
        return self.filter(member_id=member_id)

    def for_assembly(self, assembly):
        assembly_id = getattr(assembly, "pk", assembly)
        return self.filter(household__assembly_id=assembly_id)


class HouseholdMemberManager(
    models.Manager.from_queryset(HouseholdMemberQuerySet)
):
    pass


class HouseholdMember(models.Model):
    """
    Records the relationship between a Member and a Household.

    Old records remain available after a member leaves a household.
    """

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="household_memberships",
    )

    member = models.ForeignKey(
        "Member",
        on_delete=models.CASCADE,
        related_name="household_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=HouseholdRole.choices,
        default=HouseholdRole.OTHER,
    )

    is_primary_contact = models.BooleanField(default=False)

    joined_on = models.DateField(
        default=timezone.localdate,
    )

    left_on = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_household_memberships",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="updated_household_memberships",
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HouseholdMemberManager()

    class Meta:
        ordering = ["-joined_on", "-created_at"]
        verbose_name = "Household Member"
        verbose_name_plural = "Household Members"
        indexes = [
            models.Index(fields=["household", "left_on"]),
            models.Index(fields=["member", "left_on"]),
            models.Index(fields=["household", "role"]),
            models.Index(fields=["household", "is_primary_contact"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member"],
                condition=Q(left_on__isnull=True),
                name="one_active_household_per_member",
            ),
            models.UniqueConstraint(
                fields=["household"],
                condition=Q(
                    is_primary_contact=True,
                    left_on__isnull=True,
                ),
                name="one_primary_contact_per_household",
            ),
            models.CheckConstraint(
                condition=(
                    Q(left_on__isnull=True)
                    | Q(left_on__gte=models.F("joined_on"))
                ),
                name="household_left_on_after_joined_on",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.member} — {self.household}"

    @property
    def is_active(self) -> bool:
        return self.left_on is None

    def clean(self):
        errors = {}

        if self.left_on and self.left_on < self.joined_on:
            errors["left_on"] = (
                "The household departure date cannot be before the joining date."
            )

        if self.is_primary_contact and self.left_on:
            errors["is_primary_contact"] = (
                "A former household member cannot be the primary contact."
            )

        household_assembly_id = getattr(
            self.household,
            "assembly_id",
            None,
        )
        member_assembly_id = getattr(
            self.member,
            "assembly_id",
            None,
        )

        if (
            household_assembly_id
            and member_assembly_id
            and household_assembly_id != member_assembly_id
        ):
            errors["member"] = (
                "The member and household must belong to the same assembly."
            )

        if self.household.status == HouseholdStatus.CLOSED and not self.left_on:
            errors["household"] = (
                "A member cannot be added to a closed household."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def leave(
        self,
        *,
        left_on: date | None = None,
        notes: str | None = None,
        updated_by=None,
    ):
        """
        End this household membership without deleting its history.
        """
        if self.left_on:
            return self

        effective_left_on = left_on or timezone.localdate()

        if effective_left_on < self.joined_on:
            raise ValidationError(
                {
                    "left_on": (
                        "The household departure date cannot be before "
                        "the joining date."
                    )
                }
            )

        self.left_on = effective_left_on
        self.is_primary_contact = False
        self.updated_by = updated_by

        if notes is not None:
            self.notes = notes

        self.save(
            update_fields=[
                "left_on",
                "is_primary_contact",
                "notes",
                "updated_by",
                "updated_at",
            ]
        )

        return self

    def make_primary_contact(self, *, updated_by=None):
        """
        Set this member as the household's primary contact.

        The previous primary contact is automatically unset.
        """
        if self.left_on:
            raise ValidationError(
                "A former household member cannot become the primary contact."
            )

        with transaction.atomic():
            HouseholdMember.objects.select_for_update().filter(
                household=self.household,
                left_on__isnull=True,
                is_primary_contact=True,
            ).exclude(pk=self.pk).update(
                is_primary_contact=False,
                updated_by=updated_by,
                updated_at=timezone.now(),
            )

            self.is_primary_contact = True
            self.updated_by = updated_by
            self.save(
                update_fields=[
                    "is_primary_contact",
                    "updated_by",
                    "updated_at",
                ]
            )

        return self


# ---------------------------------------------------------------------------
# ASSEMBLY MEMBERSHIP AND FORMER MEMBERS
# ---------------------------------------------------------------------------









# FORMER MEMBERS PROXY
# ---------------------------------------------------------------------------


class FormerMemberQuerySet(AssemblyMembershipQuerySet):
    def transferred(self):
        return self.filter(
            end_reason=MembershipEndReason.TRANSFERRED,
        )

    def resigned(self):
        return self.filter(
            end_reason=MembershipEndReason.RESIGNED,
        )

    def relocated(self):
        return self.filter(
            end_reason=MembershipEndReason.RELOCATED,
        )

    def deceased(self):
        return self.filter(
            end_reason=MembershipEndReason.DECEASED,
        )

    def removed(self):
        return self.filter(
            end_reason=MembershipEndReason.REMOVED,
        )

    def lost_contact(self):
        return self.filter(end_reason=MembershipEndReason.LOST_CONTACT)

    def other(self):
        return self.filter(end_reason=MembershipEndReason.OTHER)


class FormerMemberManager(
    models.Manager.from_queryset(FormerMemberQuerySet)
):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(status=AssemblyMembershipStatus.ENDED)
            .select_related(
                "member",
                "assembly",
                "transfer",
                "created_by",
                "updated_by",
            )
        )


class FormerMember(AssemblyMembership):
    """
    Proxy representation of ended assembly memberships.

    This model creates no additional database table.

    A transferred member can be:
        - a former member of the source assembly;
        - an active member of the destination assembly;
        - the same permanent Member record.
    """

    objects = FormerMemberManager()

    class Meta:
        proxy = True
        ordering = ["-ended_on", "-updated_at"]
        verbose_name = "Former Member"
        verbose_name_plural = "Former Members"

    @property
    def former_assembly(self):
        return self.assembly

    @property
    def member_name(self) -> str:
        return self.member.full_name

    @property
    def reason(self) -> str:
        return self.get_end_reason_display()

    @property
    def left_on(self):
        return self.ended_on

    @property
    def current_assembly(self):
        current = self.member.current_assembly_membership
        return current.assembly if current else None

    @property
    def has_been_readmitted(self) -> bool:
        return self.member.assembly_memberships.filter(
            joined_on__gt=self.ended_on,
            status__in=[
                AssemblyMembershipStatus.ACTIVE,
                AssemblyMembershipStatus.INACTIVE,
            ],
        ).exists()

    @transaction.atomic
    def readmit(
        self,
        *,
        assembly=None,
        joined_on: date | None = None,
        created_by=None,
        household=None,
        household_role: str = HouseholdRole.OTHER,
        make_primary_contact: bool = False,
    ):
        """
        Readmit a former member by creating a new AssemblyMembership.

        The old FormerMember record remains unchanged for audit purposes.
        """
        member = (
            self.member.__class__.objects.select_for_update()
            .get(pk=self.member_id)
        )

        current_membership = (
            AssemblyMembership.objects.select_for_update()
            .current()
            .filter(member=member)
            .first()
        )

        if current_membership:
            raise ValidationError(
                {
                    "member": (
                        "This member already has a current assembly membership."
                    )
                }
            )

        target_assembly = assembly or self.assembly
        effective_joined_on = joined_on or timezone.localdate()

        new_membership = AssemblyMembership.objects.create(
            member=member,
            assembly=target_assembly,
            status=AssemblyMembershipStatus.ACTIVE,
            joined_on=effective_joined_on,
            created_by=created_by,
        )

        # Keep Member.assembly as the current assembly pointer.
        member.assembly = target_assembly
        member.updated_by = created_by
        member.save(
            update_fields=[
                "assembly",
                "updated_by",
                "updated_at",
            ]
        )

        if household is not None:
            if household.assembly_id != target_assembly.pk:
                raise ValidationError(
                    {
                        "household": (
                            "The selected household does not belong to "
                            "the destination assembly."
                        )
                    }
                )

            HouseholdMember.objects.create(
                household=household,
                member=member,
                role=household_role,
                is_primary_contact=make_primary_contact,
                joined_on=effective_joined_on,
                created_by=created_by,
            )

        return new_membership
