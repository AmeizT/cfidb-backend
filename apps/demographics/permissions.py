from rest_framework import permissions

class IsAdminOrOverseer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_overseer