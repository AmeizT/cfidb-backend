from rest_framework.permissions import BasePermission
from apps.churches.models import Zone


class CanViewZoneReport(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        zone_id = view.kwargs.get("zone_id")

        if not user or not user.is_authenticated:
            return False

        # Superuser
        if user.is_superuser:
            request.zone = Zone.objects.filter(id=zone_id).first()
            return request.zone is not None

        # Global DB staff
        if user.is_db_staff:
            request.zone = Zone.objects.filter(id=zone_id).first()
            return request.zone is not None

        # Zone Admin → only their zone
        if user.is_db_zone_staff:
            zone = Zone.objects.filter(
                id=zone_id,
                leadership__user=user   # ✅ FIXED HERE
            ).first()

            if zone:
                request.zone = zone
                return True

        return False