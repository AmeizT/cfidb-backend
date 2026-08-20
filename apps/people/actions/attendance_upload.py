import pandas as pd
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.people.models import Attendance, AttendanceCategories, WeatherCondition


class AttendanceUploadMixin:
    @action(detail=False, methods=["post"])
    def upload_excel(self, request):
        file = request.FILES.get("file")

        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        try:
            df = pd.read_excel(file)
        except Exception:
            return Response({"error": "Invalid Excel file"}, status=400)

        errors = []
        created = 0
        updated = 0

        # Normalize column names
        df.columns = [col.strip().lower() for col in df.columns]

        REQUIRED_COLUMNS = ["timestamp"]

        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                return Response(
                    {"error": f"Missing required column: {col}"},
                    status=400
                )

        user_church = getattr(request.user, "church", None)
        if user_church is None:
            return Response(
                {"error": "User does not have an associated church."},
                status=400
            )

        valid_service_types = [choice[0] for choice in AttendanceCategories]
        valid_weather_choices = [choice[0] for choice in WeatherCondition]

        # Create a mapping from lowercase human-readable names to DB values for AttendanceCategories
        service_type_map = {}
        for choice in AttendanceCategories.choices:
            db_value = choice[0]
            human_readable = choice[1]
            service_type_map[db_value.lower()] = db_value
            service_type_map[human_readable.lower()] = db_value

        # Create a mapping from lowercase human-readable names to DB values for WeatherCondition
        weather_map = {}
        for choice in WeatherCondition.choices:
            db_value = choice[0]
            human_readable = choice[1]
            weather_map[db_value.lower()] = db_value
            weather_map[human_readable.lower()] = db_value

        with transaction.atomic():
            for index, row in df.iterrows():
                debug_row = {}
                try:
                    # -------------------------
                    # 🗓 Date
                    # -------------------------
                    date_value = row.get("timestamp")

                    if pd.isna(date_value):
                        raise ValueError("Missing timestamp")

                    timestamp = pd.to_datetime(date_value, errors="coerce")

                    if pd.isna(timestamp):
                        raise ValueError(f"Invalid date: {date_value}")

                    # Convert to Python date object for Django DateField
                    timestamp = timestamp.date()

                    debug_row["timestamp"] = timestamp

                    # -------------------------
                    # 🎯 Service Type
                    # -------------------------
                    service_type_raw = row.get("service_type", "sunday")
                    if pd.isna(service_type_raw):
                        service_type_raw = "sunday"
                    service_type_key = str(service_type_raw).strip().lower()
                    if service_type_key not in service_type_map:
                        raise ValueError(f"Invalid service_type: {service_type_raw}")
                    service_type = service_type_map[service_type_key]

                    debug_row["service_type"] = service_type

                    # -------------------------
                    # 🌀 Weather
                    # -------------------------
                    weather_raw = row.get("weather", "")
                    if pd.isna(weather_raw) or str(weather_raw).strip() == "":
                        weather = None
                    else:
                        weather_key = str(weather_raw).strip().lower()
                        if weather_key not in weather_map:
                            raise ValueError(f"Invalid weather: {weather_raw}")
                        weather = weather_map[weather_key]

                    debug_row["weather"] = weather

                    # -------------------------
                    # 🔢 Numeric Fields
                    # -------------------------
                    def get_int(field):
                        val = row.get(field, 0)
                        if pd.isna(val):
                            return 0
                        try:
                            return int(val)
                        except:
                            return 0

                    special_event_name_raw = row.get("special_event_name", "")
                    if pd.isna(special_event_name_raw):
                        special_event_name = ""
                    else:
                        special_event_name = str(special_event_name_raw)

                    debug_row.update({
                        "assembly": user_church,
                        "adults": get_int("adults"),
                        "children": get_int("children"),
                        "guest_attendance": get_int("guests"),
                        "new_converts": get_int("new_converts"),
                        "altar_call": get_int("altar_call"),
                        "baptisms": get_int("baptisms"),
                        "men": get_int("men"),
                        "women": get_int("women"),
                        "visitor_men": get_int("visitor_men"),
                        "visitor_women": get_int("visitor_women"),
                        "new_convert_men": get_int("new_convert_men"),
                        "new_convert_women": get_int("new_convert_women"),
                        "altar_call_men": get_int("altar_call_men"),
                        "altar_call_women": get_int("altar_call_women"),
                        "baptism_men": get_int("baptism_men"),
                        "baptism_women": get_int("baptism_women"),
                        "online_viewers": get_int("online_viewers"),
                        "volunteers_on_duty": get_int("volunteers"),
                        "total_leaders_present": get_int("leaders"),
                        "preacher": row.get("preacher", "") if not pd.isna(row.get("preacher", "")) else "",
                        "sermon": row.get("sermon", "") if not pd.isna(row.get("sermon", "")) else "",
                        "notes": row.get("notes", "") if not pd.isna(row.get("notes", "")) else "",
                        "is_special_event": bool(row.get("is_special_event", False)),
                        "special_event_name": special_event_name,
                        "scriptures": row.get("scriptures", "") if not pd.isna(row.get("scriptures", "")) else "",
                    })

                    print(f"Row {index} debug data: {debug_row}")

                    # -------------------------
                    # 🧠 UPSERT (IMPORTANT)
                    # -------------------------
                    obj, created_flag = Attendance.objects.update_or_create(
                        assembly=user_church,
                        timestamp=timestamp,
                        service_type=service_type,
                        defaults=debug_row
                    )

                    if created_flag:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    print(f"Error on row {index}: {debug_row} Exception: {e}")
                    errors.append({
                        "row": int(index) + 2, # type: ignore
                        "error": str(e)
                    })

                print(f"Row {index}: {row.to_dict()}")
                

        return Response({
            "message": "Upload completed",
            "created": created,
            "updated": updated,
            "errors": errors
        }, status=status.HTTP_200_OK)
