from rest_framework.permissions import BasePermission


class CanManageExaminations(BasePermission):
    message = "You do not have permission to manage examinations."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        return (
            user.is_superuser
            or user.is_staff
            or user.has_perm("examinations.manage_examinations")
        )
