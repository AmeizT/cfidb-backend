from rest_framework.permissions import BasePermission


class IsDbStaff(BasePermission):
    """
    Allows access to DB staff roles, superusers, or Django staff.
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if user.is_staff:
            return True

        if hasattr(user, "is_db_staff") and user.is_db_staff:
            return True

        return False