from rest_framework import serializers
from apps.posts.models import Comment, Post, PostImage
from apps.churches.serializers import ChurchSerializer
from apps.users.serializers import ListUserSerializer
from apps.churches.models import Church
from apps.users.models import User

class AssemblySerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ['name', 'country', 'avatar_fallback']


class AuthorSerializer(serializers.ModelSerializer):
    church = AssemblySerializer()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'roles', 'church', 'avatar', 'avatar_fallback']


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()

    class Meta:
        model = Comment
        fields = ['id', 'author', 'body', 'created_at', 'updated_at']
        

class CreateCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'


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
            'author',
            'branch',
            'title',
            'body',
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
    author = AuthorSerializer()
    images = PostImageSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True)
    likes = AuthorSerializer(many=True)

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'branch',
            'title',
            'body',
            'slug',
            'likes',
            'views',
            'images',
            'comments',
            'is_private',
            'is_draft',
            'created_at',
            'updated_at'
        ]


class UpdatePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'
        


        