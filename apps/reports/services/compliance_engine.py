from datetime import date, timedelta
from django.db import transaction # type: ignore
from django.utils import timezone
from apps.reports.models.compliance import AssemblyCompliance, ZoneCompliance
from apps.reports.models import AssemblyReport
from apps.churches.models import Church, Zone

DEADLINE_DAY = 7

class ComplianceEngine:

    @staticmethod
    def evaluate_month(target_date: date = None):
        """
        Evaluate compliance for all assemblies and zones for a given month.
        If target_date is None, defaults to today.
        """
        if not target_date:
            target_date = timezone.now().date()

        first_day = target_date.replace(day=1)
        # Last day of month
        if first_day.month == 12:
            last_day = date(first_day.year, 12, 31)
        else:
            last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)

        # Evaluate all assemblies
        for assembly in Church.objects.filter(is_active=True):
            ComplianceEngine.evaluate_assembly(assembly, first_day, last_day)

        # Evaluate all zones
        for zone in Zone.objects.filter(is_active=True):
            ComplianceEngine.evaluate_zone(zone, first_day, last_day)

    @staticmethod
    @transaction.atomic
    def evaluate_assembly(assembly: Church, first_day: date, last_day: date):
        """
        Evaluate a single assembly compliance for the given month.
        """
        matching_reports = list(AssemblyReport.objects.filter(
            assembly=assembly,
            period_start=first_day,
            period_end=last_day,
        )[:2])
        report = matching_reports[0] if len(matching_reports) == 1 else None

        today = timezone.now().date()

        if report and report.is_historical_backfill:
            status = AssemblyCompliance.Status.HISTORICAL_NOT_REQUIRED
        elif not report:
            status = AssemblyCompliance.Status.NOT_SUBMITTED
        elif report.status != AssemblyReport.Status.SUBMITTED:
            status = AssemblyCompliance.Status.NOT_FINALIZED if today.day <= DEADLINE_DAY else AssemblyCompliance.Status.LATE
        elif report.submitted_at and report.submitted_at.day > DEADLINE_DAY:
            status = AssemblyCompliance.Status.LATE
        else:
            status = AssemblyCompliance.Status.COMPLIANT

        # Set year/month based on first_day
        year = first_day.year
        month = first_day.month

        AssemblyCompliance.objects.update_or_create(
            assembly=assembly,
            year=year,
            month=month,
            defaults={
                "zone": assembly.zone,
                "report": report,
                "status": status,
                "evaluated_at": timezone.now(),
            }
        )

    @staticmethod
    @transaction.atomic
    def evaluate_zone(zone: Zone, first_day: date, last_day: date):
        """
        Evaluate zone compliance by summarizing its active assemblies.
        """
        assemblies = zone.assemblies.filter(is_active=True)  # fixed related_name

        year = first_day.year
        month = first_day.month

        total_assemblies = assemblies.count()
        compliant = AssemblyCompliance.objects.filter(
            assembly__in=assemblies,
            year=year,
            month=month,
            status=AssemblyCompliance.Status.COMPLIANT
        ).count()

        compliance_rate = (compliant / total_assemblies * 100) if total_assemblies else 0

        ZoneCompliance.objects.update_or_create(
            zone=zone,
            year=year,
            month=month,
            defaults={
                "total_assemblies": total_assemblies,
                "compliant_assemblies": compliant,
                "compliance_rate": compliance_rate,
                "evaluated_at": timezone.now(),
            }
        )


