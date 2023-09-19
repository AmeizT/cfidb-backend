from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church


class Strategy(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='strategy'
    )
    
    
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "strategy"
        verbose_name_plural = "strategies"
        ordering = ["-created"]
        
    # def __str__(self):
    #     return self.title
    
    # def save(self, *args, **kwargs):                
    #     if not self.slug:
    #         base_slug = slugify(self.title)
    #         self.slug = base_slug
    #         counter = 1
    #         while Project.objects.filter(slug=self.slug).exists():
    #             self.slug = f"{base_slug}-{counter}"
    #             counter += 1

    #     super().save(*args, **kwargs)
