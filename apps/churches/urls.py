from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from apps.churches.views import ChurchView, ListChurchesView, ImageUploadView

router = DefaultRouter()

router.register(r'churches', ChurchView, basename='churches')
router.register(r'image-upload', ImageUploadView, basename='image_upload')
router.register(r'church-list', ListChurchesView, basename='church-list')

urlpatterns = [
    path('', include(router.urls)),
]



