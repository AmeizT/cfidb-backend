from django.contrib import admin

from .models import (
    JethroActionLog,
    JethroConversation,
    JethroMessage,
    JethroTitheDraft,
    JethroUsageLog,
)


@admin.register(JethroConversation)
class JethroConversationAdmin(admin.ModelAdmin):
    list_display = ("public_id", "title", "user", "assembly", "is_archived", "updated_at")
    list_filter = ("is_archived", "assembly")
    search_fields = ("public_id", "title", "user__email")


admin.site.register(JethroMessage)
admin.site.register(JethroActionLog)
admin.site.register(JethroUsageLog)
admin.site.register(JethroTitheDraft)
