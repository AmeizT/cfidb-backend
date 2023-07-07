from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.churches.views import ChurchView, ChurchManagerView

router = DefaultRouter()

router.register(r'churches', ChurchView, basename='churches')
router.register(r'manager', ChurchManagerView, basename='church_manager')

urlpatterns = [
    path('', include(router.urls)),
]



