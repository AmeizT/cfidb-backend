from rest_framework import serializers
from apps.events.models import Event
from apps.church.serializers import ChurchSerializer


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        
        
