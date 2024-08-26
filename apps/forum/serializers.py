from rest_framework import serializers
from apps.forum.models import Changelog
from apps.users.serializers import AuthorSerializer
    
class ChangelogDataSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Changelog
        fields = [
            'id',
            'author',
            'title',
            'description',
            'category',
            'image',
            'views',
            'slug',
            'is_draft',
            'created_at',
            'updated_at',
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['image'] = instance.image.url if instance.image else None
        return representation


class ChangelogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Changelog
        fields = '__all__'


