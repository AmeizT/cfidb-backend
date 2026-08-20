from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection
from django.db.models import Q

from apps.reports.services.periods import report_period


MAPPING_PATH = Path(__file__).resolve().parent / "manifests" / "finance_mapping_v1.json"
RELATIONSHIP_MAPPING_VERSION = "cfi-report-relationships-v1"
ATTENDANCE_MAPPING_VERSION = "cfi-historical-attendance-v1"


@dataclass
class MigrationResult:
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    dry_run: bool = True
    created: int = 0
    updated: int = 0
    skipped: int = 0
    conflicts: int = 0
    messages: list[str] = field(default_factory=list)
    affected_report_ids: set[int] = field(default_factory=set)

    def add(self, message, *, kind=None):
        self.messages.append(message)
        if kind:
            setattr(self, kind, getattr(self, kind) + 1)

    def payload(self):
        return {
            "run_id": str(self.run_id),
            "dry_run": self.dry_run,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "conflicts": self.conflicts,
            "mapping": mapping_metadata(),
            "messages": self.messages,
        }


def load_mapping_manifest():
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def mapping_metadata():
    raw = MAPPING_PATH.read_bytes()
    manifest = json.loads(raw)
    return {
        "version": manifest["version"],
        "checksum": hashlib.sha256(raw).hexdigest(),
        "path": str(MAPPING_PATH),
    }


def stable_checksum(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def model_checksum(instance, fields) -> str:
    return stable_checksum({field: getattr(instance, field) for field in fields})


def parse_date(value, option_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError({option_name: "Use YYYY-MM-DD."}) from exc


def filtered_assemblies(selector=None):
    from apps.churches.models import Church

    queryset = Church.objects.all().order_by("pk")
    if not selector:
        return queryset
    query = Q(code__iexact=selector)
    if str(selector).isdigit():
        query |= Q(pk=int(selector))
    matches = queryset.filter(query)
    if not matches.exists():
        raise ValidationError({"assembly": f"No assembly matches {selector!r}."})
    return matches


def assert_local_or_explicitly_authorized(*, apply=False):
    """Hard-stop accidental Phase 2 production/Neon writes."""
    config = connection.settings_dict
    host = str(config.get("HOST") or "").casefold()
    name = str(config.get("NAME") or "").casefold()
    engine = str(config.get("ENGINE") or "").casefold()
    is_neon = "neon" in host or "neon" in name
    if is_neon and os.environ.get("CFI_MIGRATION_REHEARSAL") != "1":
        raise ImproperlyConfigured(
            "Neon access is disabled for historical migration commands unless "
            "CFI_MIGRATION_REHEARSAL=1 is explicitly set on an approved rehearsal branch."
        )
    if apply and "sqlite" not in engine and os.environ.get("CFI_ALLOW_HISTORICAL_MIGRATION") != "1":
        raise ImproperlyConfigured(
            "Writes to a non-local database require CFI_ALLOW_HISTORICAL_MIGRATION=1."
        )


def is_protected_report(report) -> bool:
    return bool(
        report.current_version_id
        or report.status != report.Status.DRAFT
        or report.versions.exists()
    )


def canonical_report_for(assembly, value):
    from apps.reports.models import AssemblyReport

    start, end = report_period(value)
    touching = list(AssemblyReport.objects.filter(
        assembly=assembly,
        period_start__lte=end,
        period_end__gte=start,
    ).order_by("period_start", "period_end", "id"))
    exact = [row for row in touching if row.period_start == start and row.period_end == end]
    if len(exact) != 1 or len(touching) != 1:
        labels = ", ".join(f"#{row.pk}[{row.period_start}..{row.period_end}]" for row in touching)
        raise ValidationError({
            "report": f"Expected one canonical report for {assembly.pk}/{start:%Y-%m}; found {labels or 'none'}."
        })
    return exact[0]


def in_range(value, from_date=None, to_date=None):
    return (from_date is None or value >= from_date) and (to_date is None or value <= to_date)
