from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.posts.views import CreatePostView, PostView, CreatePostCommentView, UpdatePostView

router = DefaultRouter()

router.register(r'posts', PostView, basename='posts')
router.register(r'post/comment', CreatePostCommentView, basename='post_comment')
router.register(r'post/create', CreatePostView, basename='create_post')
router.register(r'post_update', UpdatePostView, basename='update_post')


urlpatterns = [
    path('', include(router.urls)),
]



