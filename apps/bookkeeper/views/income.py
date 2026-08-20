from django.http import Http404
from apps.bookkeeper.serializers import (
    CreateIncomeSerializer,
    IncomeSerializer,
)
from apps.bookkeeper.models import (
    Income
)
from rest_framework import viewsets, permissions
from rest_framework.permissions import BasePermission
from apps.bookkeeper.pagination import StandardPagination
from apps.users.models import DelegatePermission, PermissionType

class DelegateFinancePermission(BasePermission):
    def has_permission(self, request, view): # type: ignore
        # Grant full access to non-Delegate roles
        if request.user.roles != 'Delegate':
            return view.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']

        # Apply permissions only for Delegate role
        permission = DelegatePermission.objects.filter(
            user=request.user, permission_type=PermissionType.FINANCE
        ).first()

        # If no permission object exists for the Delegate, deny access
        if not permission:
            return False

        # Allow read operations (GET, HEAD, OPTIONS)
        if view.action in ['list', 'retrieve']:
            return True

        # For the Delegate role, enforce create/edit/delete permissions
        if view.action == 'create' and permission.can_create:
            return True
        if view.action in ['update', 'partial_update'] and permission.can_edit:
            return True
        if view.action == 'destroy' and permission.can_delete:
            return True

        return False


class IncomeView(viewsets.ModelViewSet):
    queryset = Income.objects.all()
    permission_classes = [permissions.IsAuthenticated, DelegateFinancePermission]
    pagination_class = StandardPagination
    http_method_names = ["get", "head", "options"]

    def get_serializer_class(self): # type: ignore
        if self.action == 'create':
            return CreateIncomeSerializer
        return IncomeSerializer

    def get_queryset(self): # type: ignore
        return Income.objects.filter(church=self.request.user.church)  # type: ignore






    
    
