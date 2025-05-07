from rest_framework import viewsets
from apps.announcements.models import Announcement
from apps.announcements.serializers import AnnouncementSerializer

class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        return Announcement.objects.active()