# September 2026 report backfill

`cfidb.settings.REPORT_BACKFILL` defines the enabled flag, inclusive September 1–30 window, and eligible January–August 2026 reporting periods. `is_backfill_period()` in `services/lifecycle.py` canonicalizes a report date to its calendar month and compares the complete month with the configured bounds. It evaluates the request time using Django's active timezone (default `Africa/Harare`). Tests inject aware times.

`can_complete_report()` checks the existing user/assembly access rules and `report_is_open()` before considering the window. Submitted versions without an authorised amendment, and protected stored report states, cannot receive the temporary grant. Normal amendment, submission validation, and snapshot immutability are retained. `can_create_report()` applies the same ownership check to missing periods. `ensure_report()` checks supplied actors; actor-free calls remain internal migration/model construction, not an API permission grant.

The current normal policy already permits authorised completion of open overdue reports and creation of past reports without an age cutoff. Therefore **expiry is not an automatic lock**: on October 1 the temporary grant and `backfill_active` capability disappear, and normal policy alone applies. Any new requirement to lock all old reports after September would be a separate change to normal policy.

## API flow

- `GET /api/v1/reports/{id}/` and report lists serialize `get_report_state()` capabilities.
- `GET/POST /api/v1/reports/current/?year=2026&month=1` uses the creation policy for missing-report capabilities and creation.
- Report PATCH/PUT, section updates, Attendance edits, and financial writes use the lifecycle access rules.
- Attendance/Tithes batch entry validates the active assembly, period and actor through the same policy. Source models share the open-report guard rather than independently checking for the `draft` string.
- Attendance/Tithes schemas still limit individual editable fields. Attendance row `can_edit` flags still exclude deleted and protected records.
- The frontend continues to use server capabilities → `editingDisabled` → table/column/row gates → `EditableCell`. No frontend dates or UI changes are required.

No database migration, scheduled task or expiry-day deployment is needed. The new server code must first be deployed through the usual backend deployment process.

## Verification

From the backend root:

```sh
DJANGO_ENV=LOCAL PYTHONDONTWRITEBYTECODE=1 venv/bin/python manage.py test apps.reports.test_backfill_policy apps.reports.tests.ReportLifecycleTests apps.reports.test_datatable_schemas apps.bookkeeper.tests.ManualEntryBatchApiTests apps.bookkeeper.test_soft_delete_sources --noinput
```

The tests exercise January/August creation and PATCH, protected reports, cross-assembly and anonymous callers, incomplete source data, financial batches, configuration disabling, both window boundaries, timezone midnight, and normal-policy behaviour after expiry. Tests use a separate Django test database.
