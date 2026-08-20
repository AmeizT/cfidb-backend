from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, Q


def backfill_assembly_memberships(apps, schema_editor):
    Member = apps.get_model("people", "Member")
    AssemblyMembership = apps.get_model("people", "AssemblyMembership")

    memberships = []
    for member in Member.objects.filter(assembly__isnull=False).iterator():
        start_date = member.membersince
        if not start_date and member.created_at:
            start_date = member.created_at.date()

        if start_date is None:
            continue

        memberships.append(
            AssemblyMembership(
                member_id=member.id,
                assembly_id=member.assembly_id,
                start_date=start_date,
                status="active",
            )
        )

    AssemblyMembership.objects.bulk_create(memberships, ignore_conflicts=True)


def remove_backfilled_assembly_memberships(apps, schema_editor):
    AssemblyMembership = apps.get_model("people", "AssemblyMembership")
    AssemblyMembership.objects.filter(
        status="active",
        end_date__isnull=True,
        created_by__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("churches", "0051_alter_church_code"),
        ("people", "0067_attendance_gender_split_totals"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AssemblyMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("transferred", "Transferred"), ("inactive", "Inactive")], default="active", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assembly", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="member_memberships", to="churches.church")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_assembly_memberships", to=settings.AUTH_USER_MODEL)),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assembly_memberships", to="people.member")),
            ],
            options={
                "ordering": ["-start_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="MemberTransferRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending_acceptance", "Pending acceptance"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("cancelled", "Cancelled"), ("completed", "Completed")], default="pending_acceptance", max_length=30)),
                ("effective_date", models.DateField()),
                ("reason", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_member_transfers", to=settings.AUTH_USER_MODEL)),
                ("from_assembly", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_transfer_requests", to="churches.church")),
                ("member", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="transfer_requests", to="people.member")),
                ("requested_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_member_transfers", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_member_transfers", to=settings.AUTH_USER_MODEL)),
                ("to_assembly", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="incoming_transfer_requests", to="churches.church")),
            ],
            options={
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddIndex(
            model_name="assemblymembership",
            index=models.Index(fields=["member"], name="people_asse_member__ecbaea_idx"),
        ),
        migrations.AddIndex(
            model_name="assemblymembership",
            index=models.Index(fields=["assembly"], name="people_asse_assembl_de3426_idx"),
        ),
        migrations.AddIndex(
            model_name="assemblymembership",
            index=models.Index(fields=["status"], name="people_asse_status_fa3f39_idx"),
        ),
        migrations.AddIndex(
            model_name="assemblymembership",
            index=models.Index(fields=["start_date"], name="people_asse_start_d_a4003d_idx"),
        ),
        migrations.AddIndex(
            model_name="assemblymembership",
            index=models.Index(fields=["end_date"], name="people_asse_end_dat_47c6a2_idx"),
        ),
        migrations.AddConstraint(
            model_name="assemblymembership",
            constraint=models.UniqueConstraint(condition=Q(("end_date__isnull", True), ("status", "active")), fields=("member",), name="unique_active_assembly_membership_per_member"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["member"], name="people_memb_member__d8156c_idx"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["from_assembly"], name="people_memb_from_as_ae2960_idx"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["to_assembly"], name="people_memb_to_asse_a8af76_idx"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["status"], name="people_memb_status_7047bf_idx"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["effective_date"], name="people_memb_effecti_d095e1_idx"),
        ),
        migrations.AddIndex(
            model_name="membertransferrequest",
            index=models.Index(fields=["requested_at"], name="people_memb_request_b60167_idx"),
        ),
        migrations.AddConstraint(
            model_name="membertransferrequest",
            constraint=models.CheckConstraint(condition=~Q(("from_assembly", F("to_assembly"))), name="transfer_from_and_to_assembly_must_differ"),
        ),
        migrations.AddConstraint(
            model_name="membertransferrequest",
            constraint=models.UniqueConstraint(condition=Q(("status", "pending_acceptance")), fields=("member",), name="unique_pending_transfer_per_member"),
        ),
        migrations.RunPython(
            backfill_assembly_memberships,
            remove_backfilled_assembly_memberships,
        ),
    ]
