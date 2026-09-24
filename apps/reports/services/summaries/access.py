"""Summary capabilities composed from canonical roles and existing region access."""
from django.db.models import Q
from apps.churches.models import Church, RegionLeadership
from apps.churches.services.regional_access import get_regional_staff_regions
from apps.people.permissions import is_global_transfer_admin
from apps.users.choices import UserRoles


from apps.churches.services.regional_scope import EXECUTIVE_ROLES


def executive_regions(user):
    from apps.churches.models import Region
    if user.is_superuser:
        return Region.objects.filter(is_active=True)
    return get_regional_staff_regions(user).filter(
        leadership__user=user, leadership__is_active=True,
        leadership__role__in=EXECUTIVE_ROLES,
    ).distinct()


def can_view_executive_summary(user):
    return bool(user.is_superuser or executive_regions(user).exists())


def can_view_assembly_summary(user):
    return bool(is_global_transfer_admin(user) or user.is_region_staff
                or user.roles.filter(name__in=(UserRoles.PASTOR, UserRoles.SENIOR_PASTOR)).exists()
                or user.pastor_of.exists())


def summary_assemblies(user):
    if not can_view_assembly_summary(user):
        return Church.objects.none()
    if is_global_transfer_admin(user):
        return Church.objects.all()
    # Assigned pastor/assembly relationships remain valid across assembly switching.
    return Church.objects.filter(
        Q(pk=user.church_id) | Q(branches=user) | Q(assigned_pastors=user)
        | Q(zone__region__in=get_regional_staff_regions(user))
    ).distinct()
