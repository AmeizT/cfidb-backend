from django.conf import settings
from django.db import DatabaseError
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .context import resolve_jethro_context
from .models import JethroConversation, JethroMessage
from .orchestrator import JethroProviderError, send_jethro_message
from .serializers import (
    JethroConversationSerializer,
    JethroMessageRequestSerializer,
    JethroMessageSerializer,
    TitheMemberSelectionSerializer,
)
from .tithe_services import (
    cancel_tithe_draft,
    confirm_tithe_creation,
    get_owned_draft,
    list_member_candidates,
    select_tithe_member,
)


def _replace_draft_result(draft, result):
    for message in draft.conversation.messages.filter(
        role=JethroMessage.Role.ASSISTANT,
    ).order_by("-created_at"):
        structured = message.structured_content or {}
        structured_draft = structured.get("draft") or {}
        if structured_draft.get("public_id") == draft.public_id:
            message.structured_content = result
            payment_date = result.get("payment_date") or (result.get("draft") or {}).get("payment_date")
            if result["type"] == "tithe_confirmation":
                message.content = (
                    f"Review these tithe details. Nothing will be recorded until you confirm. Payment date: {payment_date}."
                    if result["status"] == "pending_confirmation"
                    else f"This tithe draft was cancelled. Payment date: {payment_date}."
                )
            elif result["type"] == "tithe_success":
                message.content = f"The tithe was recorded successfully. Payment date: {payment_date}."
            message.save(update_fields=["content", "structured_content"])
            return


class JethroTitheDraftMixin:
    permission_classes = [permissions.IsAuthenticated]

    def context_and_draft(self, request, public_id):
        context = resolve_jethro_context(request.user)
        return context, get_owned_draft(context, public_id)


class JethroTitheMemberCandidatesView(JethroTitheDraftMixin, APIView):
    def get(self, request, public_id):
        context, draft = self.context_and_draft(request, public_id)
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
        except (TypeError, ValueError):
            raise ValidationError({"pagination": "Page and page size must be integers."})
        return Response(list_member_candidates(
            context,
            draft,
            query=request.query_params.get("query"),
            page=page,
            page_size=page_size,
        ))


class JethroTitheSelectMemberView(JethroTitheDraftMixin, APIView):
    def post(self, request, public_id):
        payload = TitheMemberSelectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        context, draft = self.context_and_draft(request, public_id)
        result = select_tithe_member(
            context,
            draft,
            payload.validated_data["member_public_id"],
        )
        _replace_draft_result(draft, result)
        return Response(result)


class JethroTitheConfirmView(JethroTitheDraftMixin, APIView):
    def post(self, request, public_id):
        context, draft = self.context_and_draft(request, public_id)
        result = confirm_tithe_creation(context, draft)
        _replace_draft_result(draft, result)
        return Response(result)


class JethroTitheCancelView(JethroTitheDraftMixin, APIView):
    def post(self, request, public_id):
        context, draft = self.context_and_draft(request, public_id)
        result = cancel_tithe_draft(context, draft)
        _replace_draft_result(draft, result)
        return Response(result)


class JethroConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JethroConversationSerializer
    lookup_field = "public_id"
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        context = resolve_jethro_context(self.request.user)
        return JethroConversation.objects.filter(user=self.request.user, assembly=context.active_assembly).prefetch_related("messages")

    def perform_create(self, serializer):
        context = resolve_jethro_context(self.request.user)
        serializer.save(user=self.request.user, assembly=context.active_assembly)


class JethroMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = JethroMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            conversation, message, usage = send_jethro_message(user=request.user, **serializer.validated_data)
        except JethroProviderError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except DatabaseError:
            return Response(
                {"detail": "Jethro could not save that request. Confirm that database migrations are applied."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            "conversation_id": conversation.public_id,
            "message": JethroMessageSerializer(message).data,
            "usage": usage,
            "mock_mode": settings.JETHRO_MOCK_MODE,
        })


class JethroStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        resolve_jethro_context(request.user)
        return Response({
            "enabled": settings.JETHRO_ENABLED,
            "mock_mode": settings.JETHRO_MOCK_MODE,
        })
