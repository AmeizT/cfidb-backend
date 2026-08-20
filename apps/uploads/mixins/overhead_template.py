from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.decorators import action


class OverheadTemplateMixin:

    @action(detail=False, methods=["get"])
    def download_overhead_template(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Overheads" # type: ignore

        headers = [
            "timestamp",
            "overhead_type",
            "amount",
            "notes",
        ]

        ws.append(headers) # type: ignore

        ws.append([ # type: ignore
            "2026-03-01",
            "Rent",
            800.00,
            "Monthly rent",
        ])

        ws.freeze_panes = "A2" # type: ignore

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=overhead_template.xlsx"

        wb.save(response)
        return response