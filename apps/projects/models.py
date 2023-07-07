from decimal import Decimal
from django.db import models
from apps.users.models import User
from apps.churches.models import Church
from django.utils.text import slugify

class Project(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    managers = models.ManyToManyField(
        User,
        related_name='project_managers',
        blank=True,
    )
    title = models.CharField(max_length=255)
    desc = models.TextField(blank=True)
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    location = models.CharField(max_length=255)
    date_start = models.DateField()
    date_end = models.DateField()
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "project"
        verbose_name_plural = "projects"
        ordering = ["-created"]
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Project.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
