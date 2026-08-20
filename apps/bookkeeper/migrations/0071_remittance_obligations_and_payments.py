from decimal import Decimal

import apps.bookkeeper.utils
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


REVENUE_CATEGORIES = [
    ("Offering", "offering", "Giving"),
    ("Fundraising", "fundraising", "Giving"),
    ("Thanksgiving", "thanksgiving", "Giving"),
    ("Donations", "donation", "Giving"),
]

OVERHEAD_TYPES = [
    ("Rent", "rent", "Facilities & Utilities"),
    ("Water", "water", "Facilities & Utilities"),
    ("Electricity", "electricity", "Facilities & Utilities"),
    ("Wages", "wage", "Staffing & Payroll"),
    ("Bank Charges", "bank charge", "Bank & Professional Fees"),
    ("Car Maintenance", "car maintenance", "Maintenance & Repairs"),
    ("Fuel", "fuel", "Transport & Travel"),
    ("Insurance", "insurance", "Insurance & Compliance"),
    ("Telephone", "telephone", "Communications & Technology"),
    ("Internet", "internet", "Communications & Technology"),
    ("Humanitarian", "humanitarian", "Ministry Operations"),
    ("Security", "security", "Facilities & Utilities"),
    ("Investment", "investment", "Operating Expenses"),
]


def seed_historical_mapping_categories(apps, schema_editor):
    RevenueCategory = apps.get_model("bookkeeper", "RevenueCategory")
    OverheadType = apps.get_model("bookkeeper", "OverheadType")
    for name, normalized_name, reporting_group in REVENUE_CATEGORIES:
        RevenueCategory.objects.get_or_create(
            assembly_id=None,
            normalized_name=normalized_name,
            defaults={
                "name": name,
                "is_standard": True,
                "is_active": True,
                "reporting_group": reporting_group,
                "needs_review": False,
            },
        )
    for name, normalized_name, reporting_group in OVERHEAD_TYPES:
        OverheadType.objects.get_or_create(
            assembly_id=None,
            normalized_name=normalized_name,
            defaults={
                "name": name,
                "is_global": True,
                "is_required": False,
                "is_active": True,
                "reporting_group": reporting_group,
                "needs_review": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("bookkeeper", "0070_remove_overheadtype_unique_overhead_type_per_assembly_and_more"),
        ("reports", "0024_historical_migration_foundation"),
    ]

    operations = [
        migrations.CreateModel(
            name="RemittanceObligation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField(db_index=True)),
                ("tithe_total_snapshot", models.DecimalField(decimal_places=2, max_digits=14)),
                ("rate", models.DecimalField(decimal_places=5, default=Decimal("0.10"), max_digits=6)),
                ("amount_due", models.DecimalField(decimal_places=2, max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assembly", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="remittance_obligations", to="churches.church")),
                ("report", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="remittance_obligation", to="reports.assemblyreport")),
                ("source_fixed_expenditure", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="migrated_remittance_obligation", to="bookkeeper.fixedexpenditure")),
            ],
            options={
                "ordering": ["period_start", "assembly_id"],
                "constraints": [models.UniqueConstraint(fields=("assembly", "period_start"), name="unique_remittance_obligation_month")],
            },
        ),
        migrations.CreateModel(
            name="RemittancePayment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_paid", models.DecimalField(decimal_places=2, max_digits=14)),
                ("payment_date", models.DateField()),
                ("receipt", models.FileField(upload_to=apps.bookkeeper.utils.remittance_receipt_path)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("verified", "Verified"), ("rejected", "Rejected")], db_index=True, default="pending", max_length=20)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("obligation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="bookkeeper.remittanceobligation")),
                ("report", models.ForeignKey(help_text="Cash-reporting month for the actual payment.", on_delete=django.db.models.deletion.PROTECT, related_name="remittance_payments", to="reports.assemblyreport")),
                ("source_fixed_expenditure", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="migrated_remittance_payments", to="bookkeeper.fixedexpenditure")),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_remittance_payments", to=settings.AUTH_USER_MODEL)),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_remittance_payments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["payment_date", "id"]},
        ),
        migrations.RunPython(seed_historical_mapping_categories, migrations.RunPython.noop),
    ]
