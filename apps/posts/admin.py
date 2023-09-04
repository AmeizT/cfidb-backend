from django.contrib import admin
from apps.posts. models import Comment, Post, PostImage, Reaction

admin.site.register(Comment)
admin.site.register(Post)
admin.site.register(PostImage)
admin.site.register(Reaction)
