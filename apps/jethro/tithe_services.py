from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bookkeeper.models import PaymentMethod, Tithe
from apps.bookkeeper.services import BatchEntryValidationError, create_tithes
from apps.people.models import Member
from apps.people.models.assembly_membership import AssemblyMembershipStatus
from apps.people.permissions import filter_membership_queryset_for_user
from apps.users.models import DelegatePermission, PermissionType

from .models import JethroActionLog, JethroTitheDraft


PAYMENT_METHOD_ALIASES = {
    "bank": PaymentMethod.BANK,
    "bank transfer": PaymentMethod.BANK,
    "transfer": PaymentMethod.BANK,
    "eft": PaymentMethod.BANK,
    "cash": PaymentMethod.CASH,
    "cheque": PaymentMethod.CHEQUE,
    "check": PaymentMethod.CHEQUE,
    "mobile": PaymentMethod.PBP,
    "mobile money": PaymentMethod.PBP,
    "payment by phone": PaymentMethod.PBP,
    "ecocash": PaymentMethod.PBP,
    "mpesa": PaymentMethod.PBP,
    "m-pesa": PaymentMethod.PBP,
    "other": PaymentMethod.OTHER,
}


def can_create_tithe(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    delegated = DelegatePermission.objects.filter(
        user=user,
        permission_type=PermissionType.FINANCE,
    ).first()
    return delegated.can_create if delegated else True


def require_tithe_permission(context):
    if not can_create_tithe(context.user):
        raise PermissionDenied(
            "You do not have permission to record tithes for this assembly."
        )


def normalize_payment_method(value):
    normalized = " ".join(str(value).strip().lower().replace("_", " ").split())
    method = PAYMENT_METHOD_ALIASES.get(normalized)
    if method is None:
        supported = ", ".join(label for _, label in PaymentMethod.choices)
        raise ValidationError({
            "payment_method": f"Unsupported payment method. Choose from: {supported}."
        })
    return method


def eligible_tithe_members(context):
    queryset = Member.objects.filter(
        assembly=context.active_assembly,
        is_trash=False,
        date_of_death__isnull=True,
        assembly_memberships__assembly=context.active_assembly,
        assembly_memberships__status=AssemblyMembershipStatus.ACTIVE,
    ).distinct()
    return filter_membership_queryset_for_user(queryset, context.user)


def _normalized(value):
    return " ".join(str(value).casefold().split())


def _member_search(queryset, query):
    normalized = _normalized(query)
    compact = "".join(normalized.split())
    tokens = normalized.split()
    lookup = Q(member_key__icontains=compact)
    for token in tokens:
        lookup |= (
            Q(first_name__icontains=token)
            | Q(middle_name__icontains=token)
            | Q(last_name__icontains=token)
        )
    candidates = list(queryset.filter(lookup).select_related("assembly")[:21])
    exact = [
        member for member in candidates
        if _normalized(member.full_name) == normalized
        or _normalized(member.member_key) == compact
    ]
    return exact or candidates


def member_summary(member):
    avatar = None
    if member.avatar:
        try:
            avatar = member.avatar.url
        except (ValueError, AttributeError):
            avatar = None
    return {
        "public_id": member.member_key,
        "member_number": member.member_key,
        "full_name": member.full_name,
        "membership_status": member.membership_status,
        "gender": member.gender,
        "assembly_name": member.assembly.name,
        "avatar": avatar,
    }


def draft_summary(draft):
    return {
        "public_id": draft.public_id,
        "status": draft.status,
        "member_query": draft.member_query,
        "member": member_summary(draft.member) if draft.member else None,
        "amount": str(draft.amount),
        "payment_method": draft.payment_method,
        "payment_date": draft.payment_date.isoformat(),
        "reference": draft.reference_code,
        "notes": draft.notes,
        "assembly_name": draft.assembly.name,
        "expires_at": draft.expires_at.isoformat(),
    }


def _selection_result(
    draft,
    candidates,
    *,
    page=1,
    page_size=10,
    total=None,
    eligible_count=None,
):
    total = len(candidates) if total is None else total
    return {
        "type": "tithe_member_selection",
        "status": JethroTitheDraft.Status.PENDING_MEMBER_SELECTION,
        "draft": draft_summary(draft),
        "results": [member_summary(member) for member in candidates],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "count": total,
            "has_next": page * page_size < total,
            "has_previous": page > 1,
        },
        "empty_reason": "no_eligible_members" if eligible_count == 0 else "no_match" if total == 0 else None,
    }


def confirmation_result(draft):
    return {
        "type": "tithe_confirmation",
        "status": JethroTitheDraft.Status.PENDING_CONFIRMATION,
        "draft": draft_summary(draft),
    }


def prepare_tithe_creation(context, arguments, conversation):
    require_tithe_permission(context)
    if conversation is None:
        raise ValidationError({"conversation": "A conversation is required."})

    payment_method = normalize_payment_method(arguments["payment_method"])
    payment_date = arguments.get("payment_date") or timezone.localdate()
    original = (
        conversation.messages.filter(role="user")
        .order_by("-created_at")
        .values_list("content", flat=True)
        .first()
        or ""
    )
    members = eligible_tithe_members(context)
    eligible_count = members.count()
    candidates = _member_search(members, arguments["member_query"])
    selected = candidates[0] if len(candidates) == 1 else None
    status = (
        JethroTitheDraft.Status.PENDING_CONFIRMATION
        if selected
        else JethroTitheDraft.Status.PENDING_MEMBER_SELECTION
    )
    draft = JethroTitheDraft.objects.create(
        user=context.user,
        assembly=context.active_assembly,
        conversation=conversation,
        member=selected,
        member_query=" ".join(arguments["member_query"].split()),
        amount=arguments["amount"],
        payment_method=payment_method,
        payment_date=payment_date,
        reference_code=arguments.get("reference", ""),
        notes=arguments.get("notes", ""),
        original_request=original,
        status=status,
        expires_at=timezone.now() + timedelta(
            minutes=settings.JETHRO_TITHE_DRAFT_TTL_MINUTES
        ),
    )
    if selected:
        return confirmation_result(draft)
    return _selection_result(
        draft,
        candidates[:10],
        total=len(candidates),
        eligible_count=eligible_count,
    )


def get_owned_draft(context, public_id):
    draft = JethroTitheDraft.objects.select_related(
        "member",
        "member__assembly",
        "assembly",
        "conversation",
        "created_tithe",
    ).filter(
        public_id=public_id,
        user=context.user,
        assembly=context.active_assembly,
    ).first()
    if draft is None:
        raise ValidationError({"draft": "Tithe draft was not found."})
    if draft.status in {
        JethroTitheDraft.Status.PENDING_MEMBER_SELECTION,
        JethroTitheDraft.Status.PENDING_CONFIRMATION,
    } and draft.expires_at <= timezone.now():
        draft.status = JethroTitheDraft.Status.EXPIRED
        draft.error_code = "expired"
        draft.save(update_fields=["status", "error_code", "updated_at"])
    return draft


def list_member_candidates(context, draft, *, query=None, page=1, page_size=10):
    if draft.status != JethroTitheDraft.Status.PENDING_MEMBER_SELECTION:
        raise ValidationError({"draft": "This draft is not awaiting member selection."})
    page = max(1, page)
    page_size = min(max(1, page_size), 20)
    queryset = eligible_tithe_members(context)
    effective_query = " ".join((draft.member_query if query is None else query).split())
    if effective_query:
        tokens = effective_query.split()
        lookup = Q(member_key__icontains="".join(tokens))
        for token in tokens:
            lookup |= (
                Q(first_name__icontains=token)
                | Q(middle_name__icontains=token)
                | Q(last_name__icontains=token)
            )
        queryset = queryset.filter(lookup)
    queryset = queryset.select_related("assembly").order_by("last_name", "first_name")
    total = queryset.count()
    start = (page - 1) * page_size
    candidates = list(queryset[start:start + page_size])
    return _selection_result(
        draft,
        candidates,
        page=page,
        page_size=page_size,
        total=total,
        eligible_count=eligible_tithe_members(context).count(),
    )


def _log_action(draft, tool_name, status, arguments=None, error=""):
    JethroActionLog.objects.create(
        user=draft.user,
        assembly=draft.assembly,
        conversation=draft.conversation,
        tool_name=tool_name,
        arguments=arguments or {},
        status=status,
        error_message=error[:255],
        duration_ms=0,
    )


@transaction.atomic
def select_tithe_member(context, draft, member_public_id):
    require_tithe_permission(context)
    locked = JethroTitheDraft.objects.select_for_update().get(pk=draft.pk)
    if locked.status != JethroTitheDraft.Status.PENDING_MEMBER_SELECTION:
        raise ValidationError({"draft": "This draft is not awaiting member selection."})
    member = eligible_tithe_members(context).filter(member_key=member_public_id).first()
    if member is None:
        raise ValidationError({"member": "The selected member is not eligible for this assembly."})
    locked.member = member
    locked.status = JethroTitheDraft.Status.PENDING_CONFIRMATION
    locked.save(update_fields=["member", "status", "updated_at"])
    locked.refresh_from_db()
    _log_action(
        locked,
        "select_tithe_member",
        JethroActionLog.Status.SUCCESS,
        {"draft_id": locked.public_id, "member_public_id": member.member_key},
    )
    return confirmation_result(locked)


def confirm_tithe_creation(context, draft):
    try:
        require_tithe_permission(context)
    except PermissionDenied:
        _log_action(
            draft,
            "confirm_tithe_creation",
            JethroActionLog.Status.REJECTED,
            {"draft_id": draft.public_id, "outcome": "rejected", "error_code": "permission_denied"},
            "Permission denied.",
        )
        raise
    expired = False
    invalid_status = False
    ineligible_member = False
    try:
        with transaction.atomic():
            locked = JethroTitheDraft.objects.select_for_update().select_related(
                "member",
                "assembly",
                "conversation",
            ).get(pk=draft.pk)
            if locked.status != JethroTitheDraft.Status.PENDING_CONFIRMATION:
                invalid_status = True
            elif locked.expires_at <= timezone.now():
                locked.status = JethroTitheDraft.Status.EXPIRED
                locked.error_code = "expired"
                locked.save(update_fields=["status", "error_code", "updated_at"])
                expired = True
            else:
                member = eligible_tithe_members(context).filter(pk=locked.member_id).first()
                if member is None:
                    ineligible_member = True
                else:
                    period = locked.payment_date.strftime("%Y-%m")
                    created, _ = create_tithes(
                        assembly=context.active_assembly,
                        user=context.user,
                        period=period,
                        entries=[{
                            "member": member,
                            "member_id": member.pk,
                            "amount": locked.amount,
                            "payment_method": locked.payment_method,
                            "timestamp": locked.payment_date,
                            "reference_code": locked.reference_code,
                            "notes": locked.notes,
                        }],
                    )
                    tithe = created[0]
                    locked.created_tithe = tithe
                    locked.status = JethroTitheDraft.Status.COMPLETED
                    locked.completed_at = timezone.now()
                    locked.error_code = ""
                    locked.save(update_fields=[
                        "created_tithe",
                        "status",
                        "completed_at",
                        "error_code",
                        "updated_at",
                    ])
                    _log_action(
                        locked,
                        "confirm_tithe_creation",
                        JethroActionLog.Status.SUCCESS,
                        {
                            "draft_id": locked.public_id,
                            "original_request": locked.original_request,
                            "member_public_id": locked.member.member_key,
                            "amount": str(locked.amount),
                            "payment_method": locked.payment_method,
                            "draft_status": locked.status,
                            "confirmation_timestamp": locked.completed_at.isoformat(),
                            "tithe_public_id": locked.public_id,
                            "outcome": "created",
                            "error_code": "",
                        },
                    )
        if expired:
            _log_action(
                locked,
                "confirm_tithe_creation",
                JethroActionLog.Status.REJECTED,
                {"draft_id": locked.public_id, "outcome": "rejected", "error_code": "expired"},
                "Draft expired.",
            )
            raise ValidationError({"draft": "This tithe draft has expired."})
        if invalid_status:
            _log_action(
                locked,
                "confirm_tithe_creation",
                JethroActionLog.Status.REJECTED,
                {"draft_id": locked.public_id, "outcome": "rejected", "error_code": f"status_{locked.status}"},
                "Draft cannot be confirmed.",
            )
            raise ValidationError({"draft": "This draft cannot be confirmed."})
        if ineligible_member:
            _log_action(
                locked,
                "confirm_tithe_creation",
                JethroActionLog.Status.REJECTED,
                {"draft_id": locked.public_id, "outcome": "rejected", "error_code": "member_ineligible"},
                "Member is no longer eligible.",
            )
            raise ValidationError({"member": "The selected member is no longer eligible."})
    except BatchEntryValidationError as exc:
        JethroTitheDraft.objects.filter(pk=draft.pk).update(
            status=JethroTitheDraft.Status.FAILED,
            error_code="finance_validation",
        )
        _log_action(
            draft,
            "confirm_tithe_creation",
            JethroActionLog.Status.ERROR,
            {
                "draft_id": draft.public_id,
                "outcome": "failed",
                "error_code": "finance_validation",
            },
            "Finance validation failed.",
        )
        raise ValidationError(exc.errors) from exc

    return {
        "type": "tithe_success",
        "status": locked.status,
        "draft_id": locked.public_id,
        "tithe_public_id": locked.public_id,
        "member": member_summary(locked.member),
        "amount": str(locked.amount),
        "payment_method": locked.payment_method,
        "payment_date": locked.payment_date.isoformat(),
        "assembly_name": locked.assembly.name,
        "reference": locked.reference_code,
        "created_at": locked.completed_at.isoformat(),
    }


@transaction.atomic
def cancel_tithe_draft(context, draft):
    locked = JethroTitheDraft.objects.select_for_update().get(pk=draft.pk)
    if locked.status not in {
        JethroTitheDraft.Status.PENDING_MEMBER_SELECTION,
        JethroTitheDraft.Status.PENDING_CONFIRMATION,
    }:
        raise ValidationError({"draft": "This draft can no longer be cancelled."})
    locked.status = JethroTitheDraft.Status.CANCELLED
    locked.save(update_fields=["status", "updated_at"])
    _log_action(
        locked,
        "cancel_tithe_creation",
        JethroActionLog.Status.SUCCESS,
        {"draft_id": locked.public_id, "draft_status": locked.status},
    )
    return {
        "type": "tithe_confirmation",
        "status": locked.status,
        "draft": draft_summary(locked),
    }
