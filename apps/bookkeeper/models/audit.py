from django.db import models

class FinancialAuditLog(models.Model):
    ACTION_CHOICES = [("CREATE","CREATE"), ("UPDATE","UPDATE"), ("DELETE","DELETE")]

    user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True)
    transaction_type = models.CharField(max_length=50)  # Income, Tithe, Expenditure, Attendance
    transaction_id = models.PositiveIntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    # def log_audit(self, user=None, action=None, old_data=None, new_data=None):
    #     from apps.users.models import User

    #     if not isinstance(user, User):
    #         user = None 

    #     FinancialAuditLog.objects.create(
    #         user=user,
    #         transaction_type="Revenue",
    #         transaction_id=self.pk or 0,
    #         action=action or "UPDATE",
    #         old_data=old_data,
    #         new_data=new_data or {
    #             "amount": str(self.amount),
    #             "notes": self.notes
    #         }
    #     )