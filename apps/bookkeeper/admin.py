from django.contrib import admin
from apps.bookkeeper.models import (
    Asset,
    Expenditure,
    FixedExpenditure,
    Income,
    Payroll,
    Pledge,
    Remittance,
    ShortfallPayment,
    Tithe
)

admin.site.register(Asset)
admin.site.register(Expenditure)
admin.site.register(FixedExpenditure)
admin.site.register(Income)
admin.site.register(Payroll)
admin.site.register(Pledge)
admin.site.register(Remittance)
admin.site.register(ShortfallPayment)
admin.site.register(Tithe)