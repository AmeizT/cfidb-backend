from django.db import models
from apps.users.models import User
from apps.church.models import Church
from django.utils.text import slugify
from apps.chat.utils import generate_umid


class Message(models.Model):    
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    )
    
    TAG_CHOICES = (
        ('praise', 'Praise'),
        ('request', 'Request'),
        ('suggestion', 'Suggestion'),
        ('testimony', 'Testimony'),
    )
    
    umid = models.CharField(
        default=generate_umid, 
        max_length=24,
        unique=True,
        editable=False
    )
    church = models.ForeignKey(
        Church, 
        related_name='message', 
        on_delete=models.CASCADE
    )
    author = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    desc = models.TextField()
    priority = models.CharField(
        max_length=24, 
        choices=PRIORITY_CHOICES, 
        default='Low'
    )
    tag = models.CharField(
        max_length=24, 
        choices=TAG_CHOICES, 
        default='request'
    )
    contact = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    isMarkAsRead = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-createdAt']
        
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
