from django.urls import path
from apps.analyzer.views import analyze_data

urlpatterns = [
    path("analyzer/", analyze_data, name="analyze-all"),
    path("analyzer/<int:assembly_id>/", analyze_data, name="analyze-assembly"),
]