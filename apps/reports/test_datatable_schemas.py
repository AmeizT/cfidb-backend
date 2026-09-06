from django.test import SimpleTestCase

from apps.reports.schemas.attendance import get_attendance_schema
from apps.reports.schemas.cashflow import get_cashflow_schema
from apps.reports.schemas.tithes import get_tithes_schema


class DataTableSchemaTests(SimpleTestCase):
    def test_tithes_uses_typed_editors_and_can_be_locked(self):
        editable = get_tithes_schema(None)
        columns = {column["id"]: column for column in editable["columns"]}

        self.assertEqual(columns["timestamp"]["formatter"], "date")
        self.assertEqual(columns["payment_method"]["editor"]["type"], "select")
        self.assertEqual(
            [option["value"] for option in columns["payment_method"]["editor"]["options"]],
            ["Bank", "Cash", "Cheque", "Mobile Money", "Other"],
        )
        self.assertTrue(editable["variant"]["interaction"]["editable"])
        self.assertFalse(
            get_tithes_schema(None, editable=False)["variant"]["interaction"]["editable"]
        )

    def test_attendance_editing_can_be_disabled_by_report_state(self):
        self.assertTrue(get_attendance_schema(None)["variant"]["interaction"]["editable"])
        self.assertFalse(
            get_attendance_schema(None, editable=False)["variant"]["interaction"]["editable"]
        )

    def test_computed_cashflow_table_is_read_only(self):
        schema = get_cashflow_schema(None)

        self.assertFalse(schema["variant"]["interaction"]["editable"])
        self.assertTrue(all(not column.get("editable", False) for column in schema["columns"]))
