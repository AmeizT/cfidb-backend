import uuid
import calendar
from PIL import Image
from decimal import Decimal
from django.db import models
from django.dispatch import receiver
from apps.users.models import User
from apps.people.models import Member
from apps.churches.models import Church
from django.db.models.signals import post_save
from cloudinary.models import CloudinaryField
from apps.bookkeeper.utils import (
    asset_image_path,
    bank_statement_path, 
    expenditure_receipt_path,
    fixed_expenditure_receipt_path,
    pledge_receipt_path,
    tithe_receipt_path, 
    remittance_receipt_path,
    shortfall_receipt_path,
    asset_images_path
)
from django.db.models import Sum
from apps.projects.models import Project
from django.db.models.functions import TruncMonth
from django.core.exceptions import ObjectDoesNotExist
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill, SmartResize


class PaymentMethod(models.TextChoices):
    BANK = 'bank', 'Bank'
    CASH = 'cash', 'Cash'
    CHEQUE = 'cheque', 'Cheque'
    EFT = 'eft', 'EFT'
    MOBILE = 'mobile', 'Mobile'
    OTHER = 'other', 'Other'
    

class Tithe(models.Model):    
    branch = models.ForeignKey(
        Church, 
        on_delete=models.PROTECT,
        related_name='assembly'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name="tithe_created_by", 
        blank=True, 
        null=True
    )
    member = models.ForeignKey(
        Member, 
        on_delete=models.PROTECT, 
        related_name='tither',
        blank=True, 
        null=True
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices, 
        default=PaymentMethod.BANK, 
    )
    receipt = models.FileField(
        upload_to=tithe_receipt_path, 
        null=True,
        blank=True, 
    )
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'tithe'
        verbose_name_plural = 'tithes'
        ordering = ['-timestamp']
        
        
    def __str__(self):
        return f'{self.member}, {self.timestamp} - {self.branch.name}'
    

class Pledge(models.Model):    
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='pledge_branch'
    )
    member = models.ForeignKey(
        Member, 
        on_delete=models.CASCADE,
        related_name='pledger'
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='project_pledge'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices, 
        default=PaymentMethod.BANK, 
    )
    receipt = models.FileField(
        upload_to=pledge_receipt_path, 
        blank=True, 
        null=True
    )
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_fulfilled = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'pledge'
        verbose_name_plural = 'pledges'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return f'{self.member.first_name} {self.member.last_name} - {self.amount}'


class Remittance(models.Model):    
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='remitter'
    )
    editor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="remittance_editor", 
        blank=True, 
        null=True
    )
    amount_due = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    shortfall = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices, 
        default=PaymentMethod.BANK, 
    )
    attachment = models.FileField(
        upload_to=remittance_receipt_path, 
        blank=True, 
        null=True
    )
    period = models.DateField(blank=False, null=True)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'remittance'
        verbose_name_plural = 'remittances'
        ordering = ['timestamp']
           
    def __str__(self):
        return f'{self.branch.name} for {self.timestamp}'
    
    def calculate_shortfall_amount(self):
        self.shortfall = self.amount_due - self.amount_paid
        if self.shortfall < 0:
            self.shortfall = Decimal(0.00)

    def save(self, *args, **kwargs):
        self.calculate_shortfall_amount()
        super().save(*args, **kwargs)
    
    @property
    def has_shortfall(self):
        return self.shortfall > 0
    

class ShortfallPayment(models.Model):
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='shortfall_branch'
    )
    remittance = models.ForeignKey(
        Remittance, 
        on_delete=models.CASCADE, 
        related_name='shortfall_payments'
    )
    editor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="shortfall_editor", 
        blank=True, 
        null=True
    )
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(0.00))
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices, 
        default=PaymentMethod.BANK, 
    )
    attachment = models.FileField(
        upload_to=shortfall_receipt_path, 
        blank=True, 
        null=True
    )
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Shortfall Payment'
        verbose_name_plural = 'Shortfall Payments'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.remittance.branch.name} for {self.timestamp}'


class FixedExpenditure(models.Model):
    assembly = models.ForeignKey(
        Church, 
        on_delete=models.PROTECT,
        related_name='fixed_expenditure'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='fixed_expenditure_editor', 
        blank=True, 
        null=True
    )
    rent = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    water = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    electricity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    telephone = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    internet = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    security = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    fuel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    wages = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    insurance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    humanitarian = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    investment = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    car_maintenance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    bank_charges = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    remittance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    remarks = models.TextField(
        blank=True
    )
    remittance_receipt = models.FileField(
        upload_to=remittance_receipt_path,
        null=True,
        blank=True
    )
    remittance_moderator = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='remittance_moderator', 
        blank=True, 
        null=True
    )
    is_remittance_verified = models.BooleanField(
        default=False
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Fixed Expenditure'
        verbose_name_plural = 'Fixed Expenditures'
        ordering = ['timestamp']
        
    def save(self, *args, **kwargs):
        self.total = self.rent + self.water + self.electricity + self.wages + self.bank_charges + self.car_maintenance + self.fuel + self.humanitarian + self.insurance + self.security + self.telephone + self.internet + self.investment
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.assembly.name} - {self.timestamp}'
    

    @receiver(post_save, sender=Tithe)
    def update_remittance(sender, instance, **kwargs):
        # Extract the month and year from the tithe's timestamp
        tithe_month = instance.timestamp.month
        tithe_year = instance.timestamp.year
        branch = instance.branch

        # Calculate the total tithes for that branch for the month and year
        total_tithes = Tithe.objects.filter(
            branch=branch, 
            timestamp__year=tithe_year, 
            timestamp__month=tithe_month
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)

        _, last_day_of_month = calendar.monthrange(tithe_year, tithe_month)

        # Calculate 25% of the total tithes for remittance
        remittance_amount = total_tithes * Decimal(0.25)

        # Ensure the FixedExpenditure timestamp matches the Tithe timestamp
        expenditure_timestamp = instance.timestamp  # Use the same date from the tithe

        # Find or create FixedExpenditure for that branch with the same timestamp
        fixed_expenditure, created = FixedExpenditure.objects.get_or_create(
            assembly=branch,
            timestamp=f"{tithe_year}-{tithe_month}-{last_day_of_month}",  # Ensure the same month and year
            defaults={'remittance': remittance_amount}
        )

        # If it's not newly created, update the remittance value
        if not created:
            fixed_expenditure.remittance = remittance_amount
            fixed_expenditure.save()

class Income(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='income'
    )
    timestamp = models.DateTimeField(
        blank=True,
        null=True
    )
    offering = models.DecimalField(
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
    donations = models.DecimalField(
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
    statement = models.FileField(
        upload_to=bank_statement_path,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'income'
        verbose_name_plural = 'income'
        ordering = ['timestamp']
        
        
    def save(self, *args, **kwargs):
        self.sum = self.offering + self.thanksgiving + self.fundraising + self.donations
        # expenses = Expenditure.objects.all().aggregate(models.Sum('total')) # type: ignore
        # self.expenses = expenses['total__sum'] or Decimal('0.00')
        # self.balance = self.sum - self.expenses
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.church.name} - {self.timestamp}'

    
    # def calculate_monthly_tithes(self):
    #     if self.timestamp is not None:
    #         month_tithes = Tithe.objects.filter(
    #             branch=self.church,
    #             created_at__date__month=self.timestamp.month,
    #             created_at__date__year=self.timestamp.year,
    #         ).aggregate(total_tithes=Sum('tithes'))['total_tithes']

    #         if month_tithes is None:
    #             month_tithes = Decimal('0.00')

    #         return month_tithes
    #     else:
    #         return Decimal('0.00')
        
        



# @receiver(post_save, sender=Tithes)
# def update_income_tithes(sender, instance, **kwargs):
#     try:
#         # Try to find an existing Income instance
#         income = Income.objects.get(church=instance.branch, timestamp__month=instance.created_at.month, timestamp__year=instance.created_at.year)
#     except ObjectDoesNotExist:
#         # If no Income instance is found, create a new one
#         income = Income(church=instance.branch, timestamp=instance.created_at)
#         income.save()

#     # Calculate and update the tithes field in the Income instance
#     income.tithes = income.calculate_monthly_tithes()
#     income.save()



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
        verbose_name = 'Bank Statement'
        verbose_name_plural = 'Bank Statements'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    

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


class Expenditure(models.Model):
    EXPENSE_TYPE_CHOICES = (
        ('amenities', 'Amenities'),
        ('conference', 'Conference'),
        ('decor', 'Decor'),
        ('fellowship', 'Fellowship'),
        ('hotel bookings', 'Hotel Bookings'),
        ('humanitarian', 'Humanitarian'),
        ('office', 'Office'),
        ('other', 'Other'),
        ('outreach', 'Outreach'),
        ('repair', 'Repair'),
        ('travel', 'Travel'),
        ('wages', 'Wages'),
    )
    
    assembly = models.ForeignKey(
        Church, 
        related_name='expenditure', 
        on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="expenditure_editor", 
        blank=True, 
        null=True
    )
    invoice_number = models.CharField(max_length=255, blank=True)
    invoice_date = models.DateField()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
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
    receipt = models.FileField(upload_to=expenditure_receipt_path, blank=True, null=True)
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













