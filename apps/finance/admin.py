from django.contrib import admin
from apps.finance.models import (
    Asset,
    Expenditure,
    Income
)

admin.site.register(Asset)
admin.site.register(Expenditure)
admin.site.register(Income)
