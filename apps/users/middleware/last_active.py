from datetime import timedelta
from django.utils.timezone import now

class LastActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            # ⛔ Prevent DB spam (only update every 5 minutes)
            if (
                not user.last_active or
                now() - user.last_active > timedelta(minutes=5)
            ):
                user.last_active = now()
                user.save(update_fields=["last_active"])

        return response