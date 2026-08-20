from decimal import Decimal
from django.db import models
from apps.churches.models import Church
from apps.bookkeeper.utils import bank_statement_path
from django.core.exceptions import ValidationError
from apps.bookkeeper.historical import NEW_FINANCE_START

class Income(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='income'
    )
    timestamp = models.DateField(
        blank=True,
        null=True
    )
    report = models.ForeignKey(
        "reports.AssemblyReport",
        on_delete=models.PROTECT,  
        null=True,                  
        blank=True,
        related_name="%(class)s_set", 
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
    total_income = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    notes = models.TextField(blank=True)
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
        if self.timestamp and self.timestamp >= NEW_FINANCE_START and not getattr(
            self, "_allow_legacy_after_cutoff", False
        ):
            raise ValidationError({
                "timestamp": "Legacy Income is read-only from 2026-08-01 onward."
            })
        self.total_income = self.offering + self.thanksgiving + self.fundraising + self.donations
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.church.name} - {self.timestamp}'
