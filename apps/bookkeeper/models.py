import uuid
from PIL import Image
from decimal import Decimal
from django.db import models
from apps.churches.models import Church
from cloudinary.models import CloudinaryField


def receipt_file_path(instance, filename):
    # 'instance' refers to the model instance, in this case, Church
    # 'filename' is the original name of the uploaded file
    # You can customize this function to generate a dynamic path as needed
    return f'files/{instance.church.name}/finance/receipt/' + filename


def bank_statement_file_path(instance, filename):
    # 'instance' refers to the model instance, in this case, Church
    # 'filename' is the original name of the uploaded file
    # You can customize this function to generate a dynamic path as needed
    return f'files/{instance.church.name}/finance/bank-statement/' + filename



class Income(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='income'
    )
    entry_date = models.DateTimeField(
        blank=True,
        null=True
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
    remittance = models.DecimalField(
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
        verbose_name = "income"
        verbose_name_plural = "income"
        ordering = ["-created_at"]
        
        
    def save(self, *args, **kwargs):
        self.sum = self.tithes + self.offering + self.pledges + self.thanksgiving + self.fundraising + self.remittance
        # expenses = Expenditure.objects.all().aggregate(models.Sum('total')) # type: ignore
        # self.expenses = expenses['total__sum'] or Decimal('0.00')
        # self.balance = self.sum - self.expenses
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Finance: {self.balance}"


class BankStatement(models.Model):
    name = models.CharField(
        max_length=255
    )
    income_entry = models.ForeignKey(
        Income,
        on_delete=models.CASCADE,
        related_name='income_entry'
    )
    attachment = CloudinaryField(
        'file', 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Bank Statement"
        verbose_name_plural = "Bank Statements"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.name


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
    description = models.TextField(blank=True)
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
    image = models.ImageField(upload_to='finance/assets/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        ordering = ["-created_at"]
        
    def __str__(self):
        return self.name



class Expenditure(models.Model):
    EXPENSE_TYPE_CHOICES = (
        ('Amenities', 'Amenities'),
        ('Conference', 'Conference'),
        ('Decor', 'Decor'),
        ('Fellowship', 'Fellowship'),
        ('Fixed', 'Fixed'),
        ('Hotel Bookings', 'Hotel Bookings'),
        ('Humanitarian', 'Humanitarian'),
        ('Office', 'Office'),
        ('Other', 'Other'),
        ('Outreach', 'Outreach'),
        ('Repair', 'Repair'),
        ('Travel', 'Travel'),
        ('Wages', 'Wages'),
    )
    
    church = models.ForeignKey(
        Church, 
        related_name='expenditure', 
        on_delete=models.CASCADE
    )
    invoice_number = models.CharField(max_length=255, blank=True)
    invoice_date = models.DateField()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
    receipt = models.FileField(upload_to='finance/expenditure/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
        
    class Meta:
        verbose_name = 'Expenditure'
        verbose_name_plural = 'Expenditure'
        ordering = ['-invoice_date']
        
    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)

    

class Payroll(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='employer', 
    )
    euid = models.CharField(max_length=255)
    date = models.DateField()
    name = models.CharField(max_length=255)
    basic = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    allowances = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    benefits = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    gross = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    deductions = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    net = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'payroll'
        verbose_name_plural = 'payrolls'
        ordering = ['-created']
        
    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        self.gross = self.basic + self.allowances + self.benefits
        self.net = self.gross - self.deductions
        super().save(*args, **kwargs)
    