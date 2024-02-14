from django.db import models
from apps.users.models import User
from django.utils.text import slugify

class AbstractBaseDocument(models.Model):
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    document_thumbnail_fallback = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        related_name='document_creator',
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
            
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):               
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while AbstractBaseDocument.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)