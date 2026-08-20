from django.contrib import admin
from apps.churches.models import (
    AssemblyCurrency,
    Church,
    ChurchMeeting,
    Forecast,
    Outreach,
    Zone,
    ZoneLeadership,
)
from apps.churches.models.region import Region, RegionLeadership

admin.site.register(AssemblyCurrency)
admin.site.register(Church)
admin.site.register(ChurchMeeting)
admin.site.register(Forecast)
admin.site.register(Outreach)
admin.site.register(Region)
admin.site.register(RegionLeadership)
admin.site.register(Zone)
admin.site.register(ZoneLeadership)
