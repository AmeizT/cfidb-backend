from django.urls import path, include
from apps.posts.views import PostView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'posts', PostView, basename='posts')

urlpatterns = [
    path('', include(router.urls)),
]



