from rest_framework import serializers
from apps.office.models import Document, Meeting, Minutes

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
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


