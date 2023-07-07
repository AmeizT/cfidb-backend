from django.contrib import admin
from apps.bookkeeper.models import (
    Asset,
    Expenditure,
    Income,
    Payroll
)

admin.site.register(Asset)
admin.site.register(Expenditure)
admin.site.register(Income)
admin.site.register(Payroll)