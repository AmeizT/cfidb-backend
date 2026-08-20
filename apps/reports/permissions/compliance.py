from rest_framework.permissions import BasePermission


class IsZoneComplianceViewer(BasePermission):
    """
    Allows:
    - Superuser
    - DB Staff
    - DB Zone Staff (with assigned zone)
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if getattr(user, "is_db_staff", False):
            return True

        if getattr(user, "is_db_zone_staff", False):
            return True

        return False
    


class IsAssemblyComplianceViewer(BasePermission):
    """
    Allows:
    - Superuser
    - DB Staff
    - DB Zone Staff (their zone only)
    - Users belonging to that assembly
    """

    def has_permission(self, request, view):

        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if getattr(user, "is_db_staff", False):
            return True

        if getattr(user, "is_db_zone_staff", False):
            return True

        # Allow authenticated users (object-level check will restrict)
        return True

    def has_object_permission(self, request, view, obj):

        user = request.user

        if user.is_superuser:
            return True

        if getattr(user, "is_db_staff", False):
            return True

        if getattr(user, "is_db_zone_staff", False):
            return obj.assembly.zone == user.zone

        # Assembly-level access
        if hasattr(user, "church") and user.church:
            return obj.assembly == user.church

        return False