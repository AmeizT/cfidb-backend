import uuid
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
    coordinator = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="strategy_coordinator", 
        blank=True, 
        null=True
    )
    strategy_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    attachment = models.FileField(
        upload_to='documents/strategy',
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
        verbose_name = "strategy"
        verbose_name_plural = "strategies"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Strategy.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        # Customize the upload_to parameter based on church and filename
        self.attachment.field.upload_to = self.generate_upload_path

        super().save(*args, **kwargs)

    def generate_upload_path(self, instance, filename):
        # Create the upload path dynamically using church and filename
        church_name = slugify(instance.church.name)  # Customize as needed
        return f"documents/strategy/{church_name}/{filename}"
