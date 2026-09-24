"""Canonical role, permitted zones and persisted regional scope."""
from apps.churches.models import Zone, RegionLeadership
from apps.churches.services.regional_access import get_regional_staff_regions

EXECUTIVE_ROLES = (RegionLeadership.Role.REGIONAL_ADMIN, RegionLeadership.Role.OVERSEER)


def uses_regional_shell(user):
    return bool(user and getattr(user, "is_authenticated", False)
        and not getattr(user, "is_superuser", False)
        and getattr(user, "region_roles", None) is not None
        and user.region_roles.filter(role__in=EXECUTIVE_ROLES, is_active=True, region__is_active=True).exists())


def permitted_zones(user):
    zones = Zone.objects.filter(is_active=True, deleted_at__isnull=True).select_related("region").order_by("name", "pk")
    if getattr(user, "is_superuser", False):
        return zones.filter(region__is_active=True)
    regions = get_regional_staff_regions(user).filter(
        leadership__user=user, leadership__is_active=True, leadership__role__in=EXECUTIVE_ROLES)
    return zones.filter(region__in=regions).distinct()


def active_zone(user):
    zones = permitted_zones(user)
    saved = getattr(user, "regional_zone_id", None)
    if saved:
        zone = zones.filter(pk=saved).first()
        if zone:
            return zone
    if not getattr(user, "is_superuser", False):
        assigned = zones.filter(leadership__user=user, leadership__is_active=True).first()
        if assigned:
            return assigned
    return zones.first()


def scope_regional_queryset(queryset, user, field="zone_id"):
    if not uses_regional_shell(user):
        return queryset
    zone = active_zone(user)
    return queryset.filter(**{field: zone.pk}) if zone else queryset.none()
