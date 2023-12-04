from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.forum.views import ForumView, ForumDataView, ForumReplyView

router = DefaultRouter()

router.register(r'forum', ForumView, basename='forum')
router.register(r'get-forum', ForumDataView, basename='get_forum')
router.register(r'forum-reply', ForumReplyView, basename='forum_reply')

urlpatterns = [
    path('', include(router.urls)),
]



