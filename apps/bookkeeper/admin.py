from django.contrib import admin
from apps.bookkeeper.models import (
    Asset,
    AssetImage,
    Expenditure,
    FinancialAuditLog,
    FixedExpenditure,
    OverheadType,
    Overhead,
    Income,
    MonthlyFinanceSnapshot,
    Revenue,
    RevenueCategory,
    RemittanceObligation,
    RemittancePayment,
    Tithe,
)

admin.site.register(Asset)
admin.site.register(AssetImage)
admin.site.register(Expenditure)
admin.site.register(FinancialAuditLog)
admin.site.register(FixedExpenditure)
admin.site.register(Income)
admin.site.register(MonthlyFinanceSnapshot)
admin.site.register(OverheadType)
admin.site.register(Overhead)
admin.site.register(Revenue)
admin.site.register(RevenueCategory)
admin.site.register(RemittanceObligation)
admin.site.register(RemittancePayment)


@admin.register(Tithe)
class TitheAdmin(admin.ModelAdmin):
    list_display = ('member', 'assembly', 'amount', 'timestamp', 'is_trash')
    list_filter = ('is_trash', 'assembly', 'payment_method')
    search_fields = ('member__full_name', 'assembly__name', 'reference_code')

    def get_queryset(self, request):
        # Show all items in admin, including trashed
        return Tithe.all_objects.all()

    actions = ['restore_selected']

    def restore_selected(self, request, queryset):
        restored_count = queryset.update(is_trash=False)
        self.message_user(request, f"{restored_count} tithes restored successfully.")
    restore_selected.short_description = "Restore selected tithes"
