import uuid
from PIL import Image
from decimal import Decimal
from django.db import models
from apps.church.models import Church
from cloudinary.models import CloudinaryField


class Income(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='income'
    )
    tithes = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    offering = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    pledges = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    fundraising = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    thanksgiving = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    funds_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    sum = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    expenses = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "finance"
        verbose_name_plural = "finances"
        ordering = ["-created_at"]
        
        
    def save(self, *args, **kwargs):
        self.sum = self.tithes + self.offering + self.pledges + self.thanksgiving + self.fundraising + self.funds_received
        expenses = Expenditure.objects.all().aggregate(models.Sum('total')) # type: ignore
        self.expenses = expenses['total__sum'] or Decimal('0.00')
        self.balance = self.sum - self.expenses
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Finance: {self.balance}"


class Expenditure(models.Model):
    EXPENSE_TYPE_CHOICES = (
        ('amenities', 'Amenities'),
        ('conference', 'Conference'),
        ('decor', 'Decor'),
        ('fellowship', 'Fellowship'),
        ('fixed', 'Fixed'),
        ('humanitarian', 'Humanitarian'),
        ('office', 'Office'),
        ('other', 'Other'),
        ('outreach', 'Outreach'),
        ('repair', 'Repair'),
        ('travel', 'Travel'),
        ('wages', 'Wages'),
    )
    
    church = models.ForeignKey(
        Church, 
        related_name='expenditure', 
        on_delete=models.CASCADE
    )
    invoice_number = models.CharField(max_length=255, blank=True)
    invoice_date = models.DateField()
    title = models.CharField(max_length=255)
    desc = models.TextField(blank=True)
    expense_type = models.CharField(
        max_length=255, 
        choices=EXPENSE_TYPE_CHOICES
    )
    supplier = models.CharField(
        max_length=255, 
        blank=True
    )
    quantity = models.IntegerField()
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'expenditure'
        verbose_name_plural = 'expenditure'
        ordering = ['-created_at']
        
    def __str__(self):
        return f'{self.title}'

    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
        
        
class Asset(models.Model):
    ASSET_TYPE_CHOICES = (
        ('Building', 'Building'),
        ('Other', 'Other'),
        ('Instrument', 'Instrument'),
        ('Vehicle', 'Vehicle'),
    )
    CONDITION_CHOICES = (
        ('New', 'New'),
        ('Good', 'Good'),
        ('Fair', 'Fair'),
        ('Old', 'Old'),
        ('Not Working', 'Not Working'),
    )
    church = models.ForeignKey(
        Church, 
        related_name='asset', 
        on_delete=models.CASCADE
    )
    asset_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    purchase_date = models.DateField()
    name = models.CharField(max_length=255)
    asset_group = models.CharField(
        max_length=255, 
        choices=ASSET_TYPE_CHOICES
    )
    description = models.TextField()
    supplier = models.CharField(max_length=255, blank=True)
    quantity = models.IntegerField()
    purchase_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    valuation = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    condition = models.CharField(
        max_length=255, 
        choices=CONDITION_CHOICES
    )
    image = CloudinaryField('image', null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.name
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     if self.image:
    #         img = Image.open(self.image.path)
    #         img.thumbnail((800, 800))
    #         img.save(self.image.path)