from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.churches.views import ChurchView, ChurchTrackerView

router = DefaultRouter()

router.register(r'churches', ChurchView, basename='churches')
router.register(r'tracker', ChurchTrackerView, basename='tracker')

urlpatterns = [
    path('', include(router.urls)),
]



