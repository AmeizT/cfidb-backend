from rest_framework import serializers
from apps.chat.models import Message
from apps.users.serializers import MinimalUserSerializer

class MessageSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Message
        fields = [
            "reference_id",
            "assembly",
            "created_by",       # for write (ID)
            "created_by_name",  # for read (full name)
            "title",
            "body",
            "priority",
            "category",
            "slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["reference_id", "slug", "created_at", "updated_at", "created_by_name"]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
    
    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)
               
class MessengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'