from decimal import Decimal
from django.db import models
from apps.users.models import User
from apps.churches.models import Church
from apps.bookkeeper.utils import (
    asset_image_path,
    asset_images_path
)
from django.db.models import Sum
from imagekit.models import ProcessedImageField
from imagekit.processors import SmartResize

class AssetType(models.TextChoices):
    BUILDING = 'Building', 'Building'
    INSTRUMENT = 'Instrument', 'Instrument'
    VEHICLE = 'Vehicle', 'Vehicle'
    FURNITURE = 'Furniture', 'Furniture'
    ELECTRONICS = 'Electronics', 'Electronics'
    MACHINERY = 'Machinery', 'Machinery'
    SOFTWARE = 'Software', 'Software'
    LAND = 'Land', 'Land'
    OTHER = 'Other', 'Other'


class Condition(models.TextChoices):
    NEW = 'New', 'New'
    GOOD = 'Good', 'Good'
    FAIR = 'Fair', 'Fair'
    OLD = 'Old', 'Old'
    NOT_WORKING = 'Not Working', 'Not Working'



class Asset(models.Model):
    assembly = models.ForeignKey(
        Church, 
        related_name='assets',
        on_delete=models.CASCADE
    )
    item_code = models.CharField(max_length=255, blank=True)
    item_name = models.CharField(max_length=255)
    acquisition_date = models.DateField()
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices
    )
    description = models.TextField(max_length=2000, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    units = models.PositiveIntegerField()
    acquisition_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    residual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=255,
        blank=True
    )
    image = ProcessedImageField(
        upload_to=asset_image_path,
        processors=[SmartResize(width=1080, height=1350)],
        format='WEBP',
        options={'quality': 70},
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assets_editor",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
        ordering = ['item_name']

    def __str__(self):
        return f"{self.assembly.name} - {self.item_name}"

class AssetImage(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='asset_images'
    )
    image = ProcessedImageField(
        upload_to=asset_images_path,
        # processors=[SmartResize(width=1080, height=1350)],
        format='WEBP', # type: ignore
        options={'quality': 80} # type: ignore
    )
    
    class Meta:
        verbose_name = 'Asset Image'
        verbose_name_plural = 'Asset Images'
        
        
    def __str__(self):
        return self.asset.item_name