from django.db.models import Count

from apps.churches.models import Church, Region
from apps.users.models import User


def get_regional_staff_regions(user):
    if not user or not user.is_authenticated:
        return Region.objects.none()

    return Region.objects.filter(
        leadership__user=user,
        leadership__is_active=True,
        is_active=True,
    ).distinct()


def get_regional_churches_queryset(user):
    regions = get_regional_staff_regions(user)

    if not regions.exists():
        return Church.objects.none()

    return (
        Church.objects.filter(zone__region__in=regions)
        .select_related("zone", "zone__region")
        .prefetch_related("assigned_pastors", "currencies")
        .annotate(
            total_members_count=Count("members", distinct=True)
            + Count("kindred", distinct=True),
            assigned_pastors_count=Count("assigned_pastors", distinct=True),
        )
        .distinct()
    )


def get_regional_users_queryset(user):
    regions = get_regional_staff_regions(user)

    if not regions.exists():
        return User.objects.none()

    return (
        User.objects.filter(church__zone__region__in=regions)
        .select_related("church", "church__zone", "church__zone__region")
        .prefetch_related("roles", "assemblies")
        .distinct()
    )
