from rest_framework.permissions import BasePermission
from apps.users.models import DelegatePermission, PermissionType

class DelegateFinancePermission(BasePermission):
    def has_permission(self, request, view):
        permission = DelegatePermission.objects.filter(
            user=request.user, permission_type=PermissionType.FINANCE
        ).first()
        
        if not permission:
            return False

        if request.method in ['POST'] and permission.can_create:
            return True
        if request.method in ['PUT', 'PATCH'] and permission.can_edit:
            return True
        if request.method == 'DELETE' and permission.can_delete:
            return True

        return False