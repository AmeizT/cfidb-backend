from decimal import Decimal
from django.db import models
from apps.users.models import User
from apps.churches.models import Church
from apps.bookkeeper.utils import (
    expenditure_receipt_path,
    remittance_receipt_path,
)
from django.core.exceptions import ValidationError
from apps.bookkeeper.historical import NEW_FINANCE_START


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
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,  
        null=True,                  
        blank=True,
        related_name="expenditure_set", 
    )
    bank_charges = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    car_maintenance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    electricity = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    fuel = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    humanitarian = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    insurance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    internet = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    investment = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    rent = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    remittance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    security = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    telephone = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    wages = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    water = models.DecimalField(
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
        verbose_name = 'Fixed Expense'
        verbose_name_plural = 'Fixed Expenses'
        ordering = ['timestamp']
        
    def save(self, *args, **kwargs):
        if self.timestamp and self.timestamp >= NEW_FINANCE_START and not getattr(
            self, "_allow_legacy_after_cutoff", False
        ):
            raise ValidationError({
                "timestamp": "Legacy FixedExpenditure is read-only from 2026-08-01 onward."
            })
        self.total = self.rent + self.water + self.electricity + self.wages + self.bank_charges + self.car_maintenance + self.fuel + self.humanitarian + self.insurance + self.security + self.telephone + self.internet + self.investment
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.assembly.name} - {self.timestamp}'
    

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
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.CASCADE,
        related_name="variable_expenditure_set",
        null=True,
        blank=True
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
    timestamp = models.DateField(null=True, blank=True, db_index=True)
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
        ordering = ['-timestamp', '-invoice_date']
        
    def __str__(self):
        return f'{self.name}'

    def assign_report(self):
        if self.report:
            return

        if not self.timestamp or not self.assembly:
            return

        from apps.reports.services.lifecycle import ensure_report

        self.report = ensure_report(assembly=self.assembly, period_start=self.timestamp)


    def save(self, *args, **kwargs):
        # Auto-set timestamp from invoice_date if missing
        if not self.timestamp and self.invoice_date:
            self.timestamp = self.invoice_date

        # Calculate total
        self.total = self.price * self.quantity

        # Assign report automatically
        self.assign_report()

        if self.report and self.report.status != self.report.Status.DRAFT:
            from django.core.exceptions import ValidationError
            raise ValidationError("Start an amendment before changing source records in a submitted report.")

        super().save(*args, **kwargs)








