from django.urls import path
from apps.analyzer.views import analyze_data

urlpatterns = [
    path("", analyze_data, name="analyze-all"),
    path("<int:assembly_id>/", analyze_data, name="analyze-assembly"),
]