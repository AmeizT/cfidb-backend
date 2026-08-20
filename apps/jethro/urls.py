from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    JethroConversationViewSet,
    JethroMessageView,
    JethroStatusView,
    JethroTitheCancelView,
    JethroTitheConfirmView,
    JethroTitheMemberCandidatesView,
    JethroTitheSelectMemberView,
)


router = SimpleRouter()
router.register("conversations", JethroConversationViewSet, basename="jethro-conversations")

urlpatterns = [
    path("", include(router.urls)),
    path("messages/", JethroMessageView.as_view(), name="jethro-messages"),
    path("status/", JethroStatusView.as_view(), name="jethro-status"),
    path("tithe-drafts/<str:public_id>/members/", JethroTitheMemberCandidatesView.as_view(), name="jethro-tithe-members"),
    path("tithe-drafts/<str:public_id>/select-member/", JethroTitheSelectMemberView.as_view(), name="jethro-tithe-select-member"),
    path("tithe-drafts/<str:public_id>/confirm/", JethroTitheConfirmView.as_view(), name="jethro-tithe-confirm"),
    path("tithe-drafts/<str:public_id>/cancel/", JethroTitheCancelView.as_view(), name="jethro-tithe-cancel"),
]
