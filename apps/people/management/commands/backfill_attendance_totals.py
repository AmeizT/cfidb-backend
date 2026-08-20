from apps.reports.management.commands.backfill_attendance_headcounts import Command as SafeCommand


class Command(SafeCommand):
    help = (
        "Compatibility alias for backfill_attendance_headcounts. "
        "It is dry-run by default and preserves historical collection semantics."
    )
