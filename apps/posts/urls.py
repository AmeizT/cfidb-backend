from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.posts.views import CreatePostView, PostView

router = DefaultRouter()

router.register(r'posts', PostView, basename='posts')
router.register(r'post/create', CreatePostView, basename='create_post')

urlpatterns = [
    path('', include(router.urls)),
]



