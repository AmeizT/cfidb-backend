from openpyxl import Workbook
from django.http import HttpResponse
from rest_framework.decorators import action
from openpyxl.worksheet.datavalidation import DataValidation
from apps.people.models import AttendanceCategories, WeatherCondition

class AttendanceTemplateMixin:

    @action(detail=False, methods=["get"])
    def download_template(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance" # type: ignore

        headers = [
            "homecell",
            "timestamp",
            "service_type",
            "is_special_event",
            "special_event_name",
            "weather",
            "men",
            "women",
            "visitor_men",
            "visitor_women",
            "new_convert_men",
            "new_convert_women",
            "altar_call_men",
            "altar_call_women",
            "baptism_men",
            "baptism_women",
            "online_viewers",
            "volunteers",
            "leaders",
            "preacher",
            "sermon",
            "scriptures",
            "notes",
        ]

        ws.append(headers) # type: ignore

        # -------------------------
        # Sample Row
        # -------------------------
        ws.append([ # type: ignore
            "",
            "2026-03-01",
            "SUNDAY",
            False,
            "",
            "SUNNY",
            60,
            70,
            4,
            6,
            2,
            1,
            3,
            2,
            1,
            0,
            50,
            12,
            8,
            "Pastor John",
            "Faith and Growth",
            "John 3:16",
            "Good service",
        ])

        # -------------------------
        # Dropdowns
        # -------------------------

        # Service Type Dropdown
        service_types = [choice[0] for choice in AttendanceCategories.choices]

        dv_service = DataValidation(
            type="list",
            formula1=f'"{",".join(service_types)}"',
            allow_blank=False
        )
        ws.add_data_validation(dv_service) # type: ignore
        dv_service.add("C2:C500")

        # Weather Dropdown
        weather_choices = [choice[0] for choice in WeatherCondition.choices]

        dv_weather = DataValidation(
            type="list",
            formula1=f'"{",".join(weather_choices)}"',
            allow_blank=True
        )
        ws.add_data_validation(dv_weather) # type: ignore
        dv_weather.add("F2:F500")

        # Boolean Dropdown (is_special_event)
        dv_bool = DataValidation(
            type="list",
            formula1='"TRUE,FALSE"',
            allow_blank=False
        )
        ws.add_data_validation(dv_bool) # type: ignore
        dv_bool.add("D2:D500")

        # Freeze header
        ws.freeze_panes = "A2" # type: ignore

        # -------------------------
        # Response
        # -------------------------
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=attendance_template.xlsx"

        wb.save(response)
        return response
