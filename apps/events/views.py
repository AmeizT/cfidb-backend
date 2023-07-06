from apps.events.models import Event
from apps.events.serializers import EventSerializer
from rest_framework import permissions, viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class EventView(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    
    
