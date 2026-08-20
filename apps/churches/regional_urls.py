from django.urls import path

from apps.churches.regional_views import RegionalChurchesView, RegionalUsersView


urlpatterns = [
    path("churches/", RegionalChurchesView.as_view(), name="regional-churches"),
    path("users/", RegionalUsersView.as_view(), name="regional-users"),
]
