from django.db import models
from apps.churches.models import Church

class MonthlyFinanceSnapshot(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name="finance_snapshots")
    year = models.IntegerField()
    month = models.IntegerField()
    gross_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tithes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    book_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.church.name} - {self.month}/{self.year}"