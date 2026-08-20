from django.urls import path, include
from apps.churches.views import ChurchView
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register(r"assemblies", ChurchView, basename="assemblies")

urlpatterns = [
    path("", include(router.urls)),
]



