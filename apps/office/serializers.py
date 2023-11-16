from rest_framework import serializers
from apps.office.models import Circular, Meeting, Minutes


class CircularSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circular
        fields = '__all__'

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'
        

class MinutesSerializer(serializers.ModelSerializer):
    meeting = MeetingSerializer()

    class Meta:
        model = Minutes
        fields = ['meeting', 'id', 'branch', 'attachment', 'created_at', 'updated_at']

class CreateMinutesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Minutes
        fields = '__all__'


