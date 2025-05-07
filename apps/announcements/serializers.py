from rest_framework import serializers
from apps.announcements.models import Announcement

class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = [
            "id", "reference", "title", "message", "slug", "platform",
            "read_more_url", "created_at", "updated_at", "expires_at", "publish_at"
        ]