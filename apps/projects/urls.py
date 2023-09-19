from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.projects.views import ( ProjectView, ProjectTrackerView )

router = DefaultRouter()

router.register(r'projects', ProjectView, basename='projects')
router.register(r'projects-tracker', ProjectTrackerView, basename='project_tracker')

urlpatterns = [
    path('', include(router.urls)),
]



