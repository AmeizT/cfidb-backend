from apps.events.models import Event
from apps.events.serializers import EventSerializer
from rest_framework import permissions, viewsets
from django_filters.rest_framework import DjangoFilterBackend


class EventView(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["church__name"]
    
    # def get_queryset(self):
    #     return Message.objects.filter(church=self.request.user.church) # type: ignore
    
    
