from django.db import models
from apps.users.models import User
from apps.churches.models import Church
from django.utils.text import slugify
from apps.chat.utils import generate_reference_id

class CategoryChoices(models.TextChoices):
    PRAISE = 'praise', 'Praise'
    REQUEST = 'request', 'Request'
    SUGGESTION = 'suggestion', 'Suggestion'
    TESTIMONY = 'testimony', 'Testimony'

class PriorityChoices(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    URGENT = 'urgent', 'Urgent'


class Message(models.Model):    
    reference_id = models.CharField(
        default=generate_reference_id, 
        max_length=24,
        unique=True,
        editable=False
    )
    assembly = models.ForeignKey(
        Church, 
        related_name='message', 
        on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name="message_author",
        blank=True,
        null=True
    )
    title = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    priority = models.CharField(
        max_length=24, 
        choices=PriorityChoices.choices, 
        default=PriorityChoices.LOW
    )
    category = models.CharField(
        max_length=24, 
        choices=CategoryChoices.choices, 
        default=CategoryChoices.REQUEST
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-created_at']
        
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Message.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    

class Comment(models.Model): 
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='commenter', 
    )   
    message = models.ForeignKey(
        Message, 
        related_name='message', 
        on_delete=models.CASCADE
    )
    comment = models.TextField()
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'comment'
        verbose_name_plural = 'comments'
        ordering = ['-createdAt']

    def __str__(self):
        return self.message.title
