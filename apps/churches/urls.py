from django.urls import path, include
from apps.churches.views import ChurchView
from apps.churches.zone_views import ZoneIdentityView
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register(r"assemblies", ChurchView, basename="assemblies")

urlpatterns = [
    path("zones/<int:pk>/identity/", ZoneIdentityView.as_view(), name="zone-identity"),
    path("", include(router.urls)),
]



