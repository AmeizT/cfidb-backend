from rest_framework import serializers
from apps.chat.models import Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        
        
class MessengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'