import pandas as pd
from .base_upload import BaseUploadService
from apps.people.models import Attendance, AttendanceCategories, Homecell, WeatherCondition

class AttendanceUploadService(BaseUploadService):
    model_name = "attendance"
    model = Attendance

    def validate_columns(self):
        if "timestamp" not in self.df.columns: # type: ignore
            raise ValueError("Missing required column: timestamp")

    def transform_row(self, row):
        user_church = getattr(self.user, "church", None)

        # Date
        timestamp = pd.to_datetime(row.get("timestamp"), errors="coerce")
        if pd.isna(timestamp):
            raise ValueError("Invalid timestamp")
        timestamp = timestamp.date()

        # Normalize
        service_type = str(row.get("service_type", "sunday")).lower().strip()
        weather = str(row.get("weather", "")).lower().strip()

        valid_service_types = [c[0] for c in AttendanceCategories.choices]
        valid_weather = [c[0] for c in WeatherCondition.choices]

        if service_type not in valid_service_types:
            raise ValueError(f"Invalid service_type: {service_type}")

        if weather and weather not in valid_weather:
            raise ValueError(f"Invalid weather: {weather}")

        def get_int(field):
            val = row.get(field, 0)
            return int(val) if pd.notna(val) else 0
        
         # -------------------------
        # Homecell lookup
        # -------------------------
        homecell = row.get("homecell")
        if pd.isna(homecell) or homecell == "":
            homecell_obj = None
        else:
            homecell_obj = Homecell.objects.filter(name__iexact=homecell, church=user_church).first()
        
        # -------------------------
        # Special event name
        # -------------------------
        special_event_name = row.get("special_event_name")
        if pd.isna(special_event_name):
            special_event_name = ""

        return {
            "assembly": user_church,
            "homecell": homecell_obj,
            "timestamp": timestamp,
            "service_type": service_type,
            "weather": weather or None,

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

            "preacher": row.get("preacher", ""),
            "sermon": row.get("sermon", ""),
            "notes": row.get("notes", ""),
            "scriptures": row.get("scriptures", ""),
            "is_special_event": bool(row.get("is_special_event", False)),
            "special_event_name": special_event_name,
        }

    def save_row(self, data):
        obj, created = Attendance.objects.update_or_create(
            assembly=data["assembly"],
            timestamp=data["timestamp"],
            service_type=data["service_type"],
            defaults=data
        )
        return created
