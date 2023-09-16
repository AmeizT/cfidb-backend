from django.shortcuts import render
from apps.chat.models import Message
from rest_framework import permissions, viewsets
from apps.chat.pagination import StandardPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.chat.serializers import MessageSerializer, MessengerSerializer


class MessageView(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    pagination_class = StandardPagination
    lookup_field = "umid"

    def get_queryset(self):
        return Message.objects.filter(church=self.request.user.church)  # type: ignore


class MessengerView(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessengerSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ["post", "put", "patch"]


class MessageAdminView(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    pagination_class = StandardPagination
    lookup_field = "umid"
