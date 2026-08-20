from django.contrib import admin
from apps.reports.models import (
    AssemblyReport,
    AuditLog,
    HistoricalMigrationLineage,
    ReportRejection,
)
from apps.reports.models.section_status import ReportSectionStatus

admin.site.register(AssemblyReport)
admin.site.register(AuditLog)
admin.site.register(ReportRejection)
admin.site.register(ReportSectionStatus)
admin.site.register(HistoricalMigrationLineage)
