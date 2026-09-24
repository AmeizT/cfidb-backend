from rest_framework import permissions

class IsAdminUserOrOverseer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_overseer", False)
                or getattr(request.user, "is_admin", False)
            )
        )


class IsRegionalStaff(permissions.BasePermission):
    """
    Allows access only to authenticated users with an active regional assignment.
    Region scoping is still enforced in each endpoint queryset.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not getattr(user, "is_region_staff", False):
            return False

        assigned_regions = getattr(user, "assigned_regions", None)

        if assigned_regions is None:
            return False

        return assigned_regions.filter(is_active=True).exists()


def can_create_assembly(user):
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_superuser
        or user.roles.filter(name="Zone Admin").exists()
        or user.zone_roles.filter(role="admin", is_active=True, zone__is_active=True).exists()
        or user.region_roles.filter(role="regional_admin", is_active=True, region__is_active=True).exists()
    )


class CanCreateAssembly(permissions.BasePermission):
    def has_permission(self, request, view):
        return can_create_assembly(request.user)
