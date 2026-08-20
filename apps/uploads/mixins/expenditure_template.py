from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.decorators import action
from openpyxl.worksheet.datavalidation import DataValidation
from apps.bookkeeper.models import Expenditure


class ExpenditureTemplateMixin:

    @action(detail=False, methods=["get"])
    def download_expenditure_template(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Expenditure" # type: ignore

        headers = [
            "invoice_date",
            "invoice_number",
            "name",
            "description",
            "category",
            "supplier",
            "quantity",
            "price",
        ]

        ws.append(headers) # type: ignore

        # -------------------------
        # Sample Row
        # -------------------------
        ws.append([ # type: ignore
            "2026-03-10",
            "INV-001",
            "Chairs Purchase",
            "Plastic chairs for church",
            "office",
            "ABC Suppliers",
            20,
            15.50,
        ])

        # -------------------------
        # Dropdown (Category)
        # -------------------------
        categories = [c[0] for c in Expenditure.EXPENSE_TYPE_CHOICES]

        dv_category = DataValidation(
            type="list",
            formula1=f'"{",".join(categories)}"',
            allow_blank=False
        )
        ws.add_data_validation(dv_category) # type: ignore
        dv_category.add("E2:E500")

        # Freeze header
        ws.freeze_panes = "A2" # type: ignore

        # -------------------------
        # Response
        # -------------------------
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=expenditure_template.xlsx"

        wb.save(response)
        return response