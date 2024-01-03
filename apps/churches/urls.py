from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.churches.views import ChurchView, ListChurchesView

router = DefaultRouter()

router.register(r'churches', ChurchView, basename='churches')
router.register(r'church-list', ListChurchesView, basename='church-list')

urlpatterns = [
    path('', include(router.urls)),
]



