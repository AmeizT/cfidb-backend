from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.people.models import (
    AssemblyMembership,
    AssemblyMembershipStatus,
    Member,
    MemberTransferRequest,
    MembershipEndReason,
)
from apps.people.permissions import can_cancel_transfer, can_create_transfer, can_review_transfer


def _actor(user):
    return user if getattr(user, "is_authenticated", False) else None


def _merge_notes(existing_notes, next_note):
    values = [value.strip() for value in (existing_notes or "", next_note or "") if value.strip()]
    return "\n".join(values)


def ensure_current_membership(member, created_by=None):
    membership = AssemblyMembership.objects.current().filter(member=member).first()
    if membership:
        return membership
    if member.assembly_id is None:
        raise ValidationError({"member": "The member has no current assembly."})

    joined_on = member.membersince
    if not joined_on or joined_on.year == 1900:
        joined_on = member.created_at.date() if member.created_at else timezone.localdate()
    return AssemblyMembership.objects.create(
        member=member,
        assembly=member.assembly,
        joined_on=joined_on,
        status=AssemblyMembershipStatus.ACTIVE,
        created_by=_actor(created_by),
    )


# Retained for callers using the old service name.
ensure_active_membership = ensure_current_membership


@transaction.atomic
def create_transfer_request(*, member, to_assembly, effective_date, reason="", notes="", requested_by=None):
    member = Member.objects.select_for_update().select_related(
        "assembly", "assembly__zone", "assembly__zone__region"
    ).get(pk=member.pk)
    if not can_create_transfer(requested_by, member):
        raise PermissionDenied("You do not have permission to transfer this member.")
    if member.assembly_id is None:
        raise ValidationError({"member": "The member has no current assembly."})
    if member.assembly_id == to_assembly.id:
        raise ValidationError({"to_assembly": "Destination must differ from the current assembly."})
    if MemberTransferRequest.objects.filter(
        member=member,
        status__in=[MemberTransferRequest.Status.PENDING, MemberTransferRequest.Status.ACCEPTED],
    ).exists():
        raise ValidationError({"member": "This member already has an open transfer request."})

    membership = ensure_current_membership(member, requested_by)
    if membership.assembly_id != member.assembly_id:
        raise ValidationError({"member": "The current membership does not match Member.assembly."})
    if effective_date < membership.joined_on:
        raise ValidationError({"effective_date": "Transfer date cannot precede the membership join date."})

    return MemberTransferRequest.objects.create(
        member=member,
        from_assembly=member.assembly,
        to_assembly=to_assembly,
        effective_date=effective_date,
        reason=reason or "",
        notes=notes or "",
        requested_by=_actor(requested_by),
    )


@transaction.atomic
def complete_transfer_request(*, transfer, completed_by=None, notes=""):
    transfer = MemberTransferRequest.objects.select_for_update().select_related(
        "from_assembly", "to_assembly"
    ).get(pk=transfer.pk)
    if not can_review_transfer(completed_by, transfer):
        raise PermissionDenied("You do not have permission to complete this transfer.")

    if transfer.status == MemberTransferRequest.Status.COMPLETED:
        destination = AssemblyMembership.objects.filter(
            member_id=transfer.member_id,
            assembly_id=transfer.to_assembly_id,
            transfer=transfer,
            status__in=[AssemblyMembershipStatus.ACTIVE, AssemblyMembershipStatus.INACTIVE],
        ).first()
        if destination is None:
            raise ValidationError("Completed transfer has no destination membership.")
        return transfer, destination
    if transfer.status not in {
        MemberTransferRequest.Status.PENDING,
        MemberTransferRequest.Status.ACCEPTED,
    }:
        raise ValidationError("Only pending or accepted transfers can be completed.")
    if transfer.from_assembly_id == transfer.to_assembly_id:
        raise ValidationError("Source and destination assemblies must differ.")

    member = Member.objects.select_for_update().get(pk=transfer.member_id)
    if member.assembly_id != transfer.from_assembly_id:
        raise ValidationError("The member no longer belongs to the source assembly.")
    source = AssemblyMembership.objects.select_for_update().current().filter(member=member).first()
    if source is None:
        source = ensure_current_membership(member, completed_by)
    if source.assembly_id != transfer.from_assembly_id:
        raise ValidationError("The current membership does not match the transfer source assembly.")
    if transfer.effective_date < source.joined_on:
        raise ValidationError("Transfer date cannot precede the source membership join date.")

    try:
        source = source.end_membership(
            reason=MembershipEndReason.TRANSFERRED,
            ended_on=transfer.effective_date,
            transfer=transfer,
            updated_by=_actor(completed_by),
            close_household_membership=True,
            clear_member_assembly=False,
        )
        destination = AssemblyMembership.objects.create(
            member=member,
            assembly=transfer.to_assembly,
            status=AssemblyMembershipStatus.ACTIVE,
            joined_on=transfer.effective_date,
            transfer=transfer,
            created_by=_actor(completed_by),
            updated_by=_actor(completed_by),
        )
    except (DjangoValidationError, IntegrityError) as exc:
        raise ValidationError(getattr(exc, "message_dict", None) or str(exc)) from exc

    member.assembly = transfer.to_assembly
    member.updated_by = _actor(completed_by)
    member.save(update_fields=["assembly", "updated_by", "updated_at"])

    now = timezone.now()
    transfer.status = MemberTransferRequest.Status.COMPLETED
    transfer.reviewed_by = _actor(completed_by)
    transfer.completed_by = _actor(completed_by)
    transfer.reviewed_at = transfer.reviewed_at or now
    transfer.completed_at = transfer.completed_at or now
    transfer.notes = _merge_notes(transfer.notes, notes)
    transfer.save(update_fields=[
        "status", "reviewed_by", "completed_by", "reviewed_at", "completed_at", "notes", "updated_at"
    ])
    return transfer, destination


def accept_transfer_request(*, transfer, reviewed_by=None, notes=""):
    transfer, _ = complete_transfer_request(
        transfer=transfer, completed_by=reviewed_by, notes=notes
    )
    return transfer


@transaction.atomic
def reject_transfer_request(*, transfer, reviewed_by=None, rejection_reason="", notes=""):
    transfer = MemberTransferRequest.objects.select_for_update().get(pk=transfer.pk)
    if not can_review_transfer(reviewed_by, transfer):
        raise PermissionDenied("You do not have permission to reject this transfer.")
    if transfer.status != MemberTransferRequest.Status.PENDING:
        raise ValidationError("Only pending transfer requests can be rejected.")
    rejection_reason = (rejection_reason or "").strip()
    if not rejection_reason:
        raise ValidationError({"rejection_reason": "Rejection reason is required."})
    transfer.status = MemberTransferRequest.Status.REJECTED
    transfer.reviewed_by = _actor(reviewed_by)
    transfer.reviewed_at = timezone.now()
    transfer.rejection_reason = rejection_reason
    transfer.notes = _merge_notes(transfer.notes, notes)
    transfer.save(update_fields=[
        "status", "reviewed_by", "reviewed_at", "rejection_reason", "notes", "updated_at"
    ])
    return transfer


@transaction.atomic
def cancel_transfer_request(*, transfer, cancelled_by=None, notes=""):
    transfer = MemberTransferRequest.objects.select_for_update().get(pk=transfer.pk)
    if not can_cancel_transfer(cancelled_by, transfer):
        raise PermissionDenied("You do not have permission to cancel this transfer.")
    if transfer.status != MemberTransferRequest.Status.PENDING:
        raise ValidationError("Only pending transfer requests can be cancelled.")
    transfer.status = MemberTransferRequest.Status.CANCELLED
    transfer.reviewed_by = _actor(cancelled_by)
    transfer.reviewed_at = timezone.now()
    transfer.notes = _merge_notes(transfer.notes, notes)
    transfer.save(update_fields=["status", "reviewed_by", "reviewed_at", "notes", "updated_at"])
    return transfer
