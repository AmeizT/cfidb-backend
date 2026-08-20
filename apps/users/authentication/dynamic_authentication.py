from typing import Optional, Tuple
from rest_framework import exceptions
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BaseAuthentication
from .cookies import CookieJWTAuthentication

class DynamicAuthentication(BaseAuthentication):
    """
    Dynamically selects authentication backend:
    - Uses CookieJWTAuthentication if no Authorization header is present (frontend/browser)
    - Uses JWTAuthentication if Authorization header is present (API clients, Postman, ThunderClient)
    """

    def authenticate(self, request) -> Optional[Tuple[object, object]]:
        # 1️⃣ Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            # Use standard JWT
            try:
                return JWTAuthentication().authenticate(request)
            except exceptions.AuthenticationFailed as e:
                raise exceptions.AuthenticationFailed(f"JWT auth failed: {str(e)}")

        # 2️⃣ Fallback to CookieJWTAuthentication (frontend)
        try:
            result = CookieJWTAuthentication().authenticate(request)
            if result is None:
                # No cookie found, anonymous user
                return (AnonymousUser(), None)
            return result
        except exceptions.AuthenticationFailed as e:
            raise exceptions.AuthenticationFailed(f"Cookie auth failed: {str(e)}")