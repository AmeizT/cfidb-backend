from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.forum.views import ChangelogView

router = DefaultRouter()

router.register(r'changelog', ChangelogView, basename='changelog')

urlpatterns = [
    path('', include(router.urls)),
]



