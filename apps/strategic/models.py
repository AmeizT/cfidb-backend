import uuid
from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from imagekit.processors import ResizeToFill
from imagekit.models import ProcessedImageField
from apps.strategic.helpers import strategy_banner_path, strategy_file_path


class StatusChoices(models.TextChoices):
    PENDING = 'Pending', 'Pending'
    APPROVED = 'Approved', 'Approved'
    DISAPPROVE = 'Disapproved', 'Disapproved'

class StrategyLegacy(models.Model):
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='strategy_legacy'
    )
    coordinator = models.CharField(max_length=255, blank=True)
    title = models.CharField(
        max_length=255,
        blank=True
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
    color = models.CharField(max_length=12, blank=True)
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
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='strategy'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="strategic_plan_author", 
        blank=True, 
        null=True
    )
    coordinator = models.CharField(max_length=255, blank=True)
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
    banner = ProcessedImageField(
        upload_to=strategy_banner_path,
        processors=[ResizeToFill(640, 360)], # type: ignore
        format='WEBP', # type: ignore
        options={'quality': 100},
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=255,
        choices=StatusChoices.choices, 
        default=StatusChoices.PENDING, 
    )
    feedback = models.TextField(blank=True)
    banner_fallback = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'strategy'
        verbose_name_plural = 'strategies'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return self.branch.name
        
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Strategy.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)
    
    
