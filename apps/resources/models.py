import os
import uuid
from PIL import Image
from django.db import models
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
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=storageURL, null=True, blank=True)
    file = models.FileField(upload_to='uploads/', validators=[validate_non_image_file])
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resource"
        verbose_name_plural = "Resources"
        ordering = ["name"]

    def __str__(self):
        return self.name

    


