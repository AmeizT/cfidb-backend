from rest_framework import permissions
from django.db.models import Q

class IsAdminOrOverseer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_overseer


class CanManageMembers(permissions.BasePermission):
    """Allow authenticated creation; keep existing roles for other member writes."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if getattr(view, "action", None) == "create":
            return True
        return bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_admin", False)
            or getattr(user, "is_staff", False)
            or getattr(user, "is_db_staff", False)
            or getattr(user, "is_region_staff", False)
            or getattr(user, "is_db_zone_staff", False)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return can_access_assembly(request.user, obj.assembly)


def is_global_transfer_admin(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    return any([
        getattr(user, "is_superuser", False),
        getattr(user, "is_admin", False),
        getattr(user, "is_db_staff", False),
    ])


def get_user_transfer_assembly_ids(user):
    """Return the authenticated user's active assembly, never client scope."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    church_id = getattr(user, "church_id", None)
    return {church_id} if church_id else set()


def get_user_transfer_region_ids(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    if not getattr(user, "is_region_staff", False):
        return set()

    assigned_regions = getattr(user, "assigned_regions", None)
    if assigned_regions is None:
        return set()

    return set(assigned_regions.filter(is_active=True).values_list("id", flat=True))


def can_access_assembly(user, assembly):
    if is_global_transfer_admin(user):
        return True

    assembly_id = getattr(assembly, "id", assembly)
    if assembly_id in get_user_transfer_assembly_ids(user):
        return True

    region_id = getattr(getattr(assembly, "zone", None), "region_id", None)
    return bool(region_id and region_id in get_user_transfer_region_ids(user))


def can_view_transfer(user, transfer):
    return (
        can_access_assembly(user, transfer.from_assembly)
        or can_access_assembly(user, transfer.to_assembly)
    )


def can_create_transfer(user, member):
    return can_access_assembly(user, member.assembly)


def can_review_transfer(user, transfer):
    return can_access_assembly(user, transfer.to_assembly)


def can_cancel_transfer(user, transfer):
    return can_access_assembly(user, transfer.from_assembly)


def filter_transfer_queryset_for_user(queryset, user, direction=None):
    if is_global_transfer_admin(user):
        return queryset

    assembly_ids = get_user_transfer_assembly_ids(user)
    region_ids = get_user_transfer_region_ids(user)
    query = Q(pk__in=[])

    if direction == "incoming":
        if assembly_ids:
            query |= Q(to_assembly_id__in=assembly_ids)
        if region_ids:
            query |= Q(to_assembly__zone__region_id__in=region_ids)
    elif direction == "outgoing":
        if assembly_ids:
            query |= Q(from_assembly_id__in=assembly_ids)
        if region_ids:
            query |= Q(from_assembly__zone__region_id__in=region_ids)
    else:
        if assembly_ids:
            query |= Q(from_assembly_id__in=assembly_ids) | Q(to_assembly_id__in=assembly_ids)
        if region_ids:
            query |= (
                Q(from_assembly__zone__region_id__in=region_ids)
                | Q(to_assembly__zone__region_id__in=region_ids)
            )

    return queryset.filter(query).distinct()


def filter_membership_queryset_for_user(queryset, user):
    if is_global_transfer_admin(user):
        return queryset

    assembly_ids = get_user_transfer_assembly_ids(user)
    region_ids = get_user_transfer_region_ids(user)
    query = Q(pk__in=[])

    if assembly_ids:
        query |= Q(assembly_id__in=assembly_ids)

    if region_ids:
        query |= Q(assembly__zone__region_id__in=region_ids)

    return queryset.filter(query).distinct()
