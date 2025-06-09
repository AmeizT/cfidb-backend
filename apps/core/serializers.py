from rest_framework import serializers
from apps.users.serializers import MinimalUserSerializer
from apps.core.models import Blog, Documentation, TOS, TOSAcceptance

class DocumentationSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Documentation
        fields = ["id", "title", "body", "category", "status", "author", "author_name", "created_at", "updated_at"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]


class BlogSerializer(serializers.ModelSerializer):
    author = MinimalUserSerializer()
    
    class Meta:
        model = Blog
        fields = ['id', 'author', 'title', 'subtitle', 'body', 'category', 'image', 'created_at', 'updated_at', 'status', 'slug']

class TOSSerializer(serializers.ModelSerializer):
    class Meta:
        model = TOS
        fields = ['id', 'title', 'content', 'version', 'created_at', 'updated_at']

class TOSAcceptanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TOSAcceptance
        fields = ['user', 'terms', 'accepted_at']
        read_only_fields = ['user', 'accepted_at']