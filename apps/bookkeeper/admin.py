from django.contrib import admin
from apps.bookkeeper.models import (
    Asset,
    Expenditure,
    FixedExpenditure,
    Income,
    MonthlyFinanceSnapshot,
    Payroll,
    Pledge,
    Remittance,
    ShortfallPayment,
    Tithe,
    AssetImage
)

admin.site.register(Asset)
admin.site.register(AssetImage)
admin.site.register(Expenditure)
admin.site.register(FixedExpenditure)
admin.site.register(Income)
admin.site.register(MonthlyFinanceSnapshot)
# admin.site.register(Payroll)
# admin.site.register(Pledge)
# admin.site.register(Remittance)
# admin.site.register(ShortfallPayment)
admin.site.register(Tithe)