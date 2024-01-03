import os
import uuid
from PIL import Image
from django.db import models
from django.utils.text import slugify
from imagekit.processors import ResizeToFill
from imagekit.models import ProcessedImageField
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_non_image_file(value):
        ext = os.path.splitext(value.name)[1]
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            raise ValidationError("Only non-image files are allowed.")


def storageURL(instance, filename):
    return "resources/{filename}".format(filename=filename)


class Resource(models.Model):
    ruid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to='uploads/', 
        blank=True,
        null=True,
        # validators=[validate_non_image_file]
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    resource_image_fallback = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resource"
        verbose_name_plural = "Resources"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Resource.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)

    


