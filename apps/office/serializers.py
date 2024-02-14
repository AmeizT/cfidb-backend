from rest_framework import serializers
from apps.office.models import Circular, Meeting, Minutes, Strategy

class CircularSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circular
        fields = '__all__'


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'
        

class GetMinutesSerializer(serializers.ModelSerializer):
    meeting = MeetingSerializer()

    class Meta:
        model = Minutes
        fields = ['id', 'meeting', 'assembly', 'attachment', 'created_at', 'updated_at']
        

class MinutesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Minutes
        fields = '__all__'


class StrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = Strategy
        fields = '__all__'


