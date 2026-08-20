from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.decorators import action


class RevenueTemplateMixin:

    @action(detail=False, methods=["get"])
    def download_revenue_template(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Revenue" # type: ignore

        headers = [
            "timestamp",
            "category",
            "amount",
            "notes",
        ]

        ws.append(headers) # type: ignore

        # Sample
        ws.append([ # type: ignore
            "2026-03-01",
            "Tithes",
            1500.00,
            "Sunday collection",
        ])

        ws.freeze_panes = "A2" # type: ignore

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=revenue_template.xlsx"

        wb.save(response)
        return response