from rest_framework import serializers
from apps.posts.models import Comment, Post, PostImage, Like
from apps.churches.serializers import ChurchSerializer
from apps.users.serializers import ListUserSerializer


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = '__all__'
        

class CreatePostSerializer(serializers.ModelSerializer):
    images = PostImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True
    )
    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'branch',
            'title',
            'description',
            'slug',
            'views',
            'images',
            'uploaded_images',
            'is_private',
            'is_draft',
            'created_at',
            'updated_at'
        ]

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images')

        # Create the Post object
        post = Post.objects.create(**validated_data)

        # Create PostImage objects for uploaded images
        for image in uploaded_images:
            PostImage.objects.create(post=post, image=image)

        return post


class PostSerializer(serializers.ModelSerializer):
    branch = ChurchSerializer()
    author = ListUserSerializer()
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'branch',
            'title',
            'description',
            'slug',
            'likes',
            'views',
            'images',
            'is_private',
            'is_draft',
            'created_at',
            'updated_at'
        ]


        


        