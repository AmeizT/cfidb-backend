from rest_framework import permissions

class IsAdminUserOrOverseer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_overseer or request.user.is_admin