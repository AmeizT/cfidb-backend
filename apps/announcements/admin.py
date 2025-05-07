from django.contrib import admin
from django.utils.timezone import now
from .models import Announcement

# Custom Filters — move these OUTSIDE the admin class
class ActiveFilter(admin.SimpleListFilter):
    title = "active"
    parameter_name = "active"

    def lookups(self, request, model_admin):
        return [("yes", "Active"), ("no", "Inactive")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(publish_at__lte=now(), expires_at__gt=now())
        if self.value() == "no":
            return queryset.exclude(publish_at__lte=now(), expires_at__gt=now())
        return queryset


class ScheduledFilter(admin.SimpleListFilter):
    title = "scheduled"
    parameter_name = "scheduled"

    def lookups(self, request, model_admin):
        return [("yes", "Scheduled"), ("no", "Not Scheduled")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(publish_at__gt=now())
        if self.value() == "no":
            return queryset.filter(publish_at__lte=now())
        return queryset


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("reference", "title", "platform", "publish_at", "expires_at", "is_expired", "is_published")
    list_filter = (
        "platform",
        "created_at",
        "expires_at",
        "publish_at",
        ActiveFilter,
        ScheduledFilter,
    )
    search_fields = ("title", "message", "slug", "reference")
    readonly_fields = ("reference",)

    def is_published(self, obj):
        return obj.publish_at <= now()
    is_published.boolean = True

    def is_expired(self, obj):
        return obj.expires_at <= now()
    is_expired.boolean = True