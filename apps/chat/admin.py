from django.contrib import admin
from apps.chat.models import Message, Comment


admin.site.register(Message)
admin.site.register(Comment)
