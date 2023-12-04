from rest_framework import serializers
from apps.forum.models import Forum, Reply
from apps.users.serializers import ListUserSerializer

class ForumReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Reply
        fields = '__all__'
        

class ForumReplyDataSerializer(serializers.ModelSerializer):
    author = ListUserSerializer()
    
    class Meta:
        model = Reply
        fields = ['discussion', 'author', 'description', 'created_at', 'updated_at']

    
class ForumDataSerializer(serializers.ModelSerializer):
    author = ListUserSerializer()
    replies = ForumReplyDataSerializer(many=True)

    class Meta:
        model = Forum
        fields = [
            'id',
            'author',
            'title',
            'description',
            'category',
            'image',
            'viewCount',
            'slug',
            'is_draft',
            'created_at',
            'updated_at',
            'replies',
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = instance.image.url if instance.image else None
        return representation


class ForumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Forum
        fields = '__all__'


