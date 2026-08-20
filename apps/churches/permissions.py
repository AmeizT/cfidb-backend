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
