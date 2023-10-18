import uuid
from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church


def strategy_file_path(instance, filename):
    return 'cfidb/strategy/{0}/{1}/{2}'.format(
        instance.branch.name,  
        instance.timestamp,  
        filename
    )

class StrategyLegacy(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True, 
        editable=False, 
        unique=True
    )
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='strategy_legacy'
    )
    coordinator = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='strategy_coordinator', 
        blank=True, 
        null=True
    )
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    attachment = models.FileField(
        upload_to=strategy_file_path,
        null=True,
        blank=True
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Strategy Legacy'
        verbose_name_plural = 'Strategy Legacy'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while StrategyLegacy.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)



class Strategy(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True, 
        editable=False, 
        unique=True
    )
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='strategy'
    )
    introduction = models.TextField(
        blank=True
    )
    financial_mandate = models.TextField(
        blank=True
    )
    capacity_development = models.TextField(
        blank=True
    )
    infrastructure_development = models.TextField(
        blank=True
    )
    church_growth = models.TextField(
        blank=True
    )
    humanitarian_projects = models.TextField(
        blank=True
    )
    accountability = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        verbose_name = 'strategy'
        verbose_name_plural = 'strategies'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return self.branch.name
