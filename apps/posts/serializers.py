from rest_framework import serializers
from apps.posts.models import Comment, Post, PostImage, Reaction
from apps.churches.serializers import ChurchSerializer


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'post', 'image', 'caption']
        

class PostSerializer(serializers.ModelSerializer):
    author = ChurchSerializer()
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 
            'author',
            'title', 
            'description',
            'slug',
            'views', 
            'images',
            'is_private',
            'is_draft', 
            'created_at', 
            'updated_at'
        ]
        