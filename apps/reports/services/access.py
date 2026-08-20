from apps.churches.models.assembly import Church


def get_accessible_assemblies(user):
    if user.is_superuser:
        return Church.objects.all()

    if user.is_zone_admin:
        return Church.objects.filter(
            zone=user.zone
        )

    if user.is_region_overseer:
        return Church.objects.filter(
            zone__region=user.region
        )

    return Church.objects.none()