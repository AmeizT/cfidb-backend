from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.reports.models import AssemblyReport
from apps.reports.services.compliance_engine import ComplianceEngine


@receiver(post_save, sender=AssemblyReport)
def auto_recalculate_compliance(sender, instance, **kwargs):
    if instance.status == AssemblyReport.Status.SUBMITTED and instance.assembly.zone_id:
        ComplianceEngine.evaluate_assembly(
            assembly=instance.assembly,
            first_day=instance.period_start,
            last_day=instance.period_end,
        )

        ComplianceEngine.evaluate_zone(
            zone=instance.assembly.zone,
            first_day=instance.period_start,
            last_day=instance.period_end,
        )
