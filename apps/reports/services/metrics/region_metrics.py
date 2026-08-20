def get_region_dashboard(region):
    zones = region.zones.all()

    return {
        "zones": zones.count(),
        "assemblies": sum(
            z.churches.count()
            for z in zones
        ),
    }



from apps.churches.models import Zone
from apps.reports.services.metrics.zone_metrics import get_zone_metrics


def get_region_metrics(region, year, month=None):
    zones = Zone.objects.filter(region=region)

    zone_data = [
        get_zone_metrics(zone, year, month)
        for zone in zones
    ]

    return {
        "region": {
            "id": region.id,
            "name": region.name,
        },

        "summary": {
            "zones": len(zone_data),
            "assemblies": sum(z["summary"]["assemblies"] for z in zone_data),
        },

        "zones": zone_data,
    }