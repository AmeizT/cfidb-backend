from rest_framework import serializers
from apps.churches.models import Zone


class ZoneIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ("id", "name", "region", "zone_avatar", "zone_avatar_fallback")
        read_only_fields = ("id", "name", "region")
