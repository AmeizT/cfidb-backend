import jwt
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

IS_DEBUG = settings.DEBUG


class JWTRefreshMiddleware(MiddlewareMixin):
    def process_request(self, request):
        access_token = request.COOKIES.get("accessToken")
        refresh_token = request.COOKIES.get("refreshToken")

        if not access_token or not refresh_token:
            return None

        try:
            # ✅ Token still valid
            AccessToken(access_token)

            # 🔥 IMPORTANT: Inject header so DRF sees it
            request.META["HTTP_AUTHORIZATION"] = f"JWT {access_token}"

            print("Access token valid, no refresh needed.")
            return None

        except TokenError:
            print("Access token expired, attempting refresh...")

            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)

                # ✅ Inject new token
                request.META["HTTP_AUTHORIZATION"] = f"JWT {new_access_token}"

                request._new_access_token = new_access_token

            except TokenError:
                return None

    def process_response(self, request, response):
        new_token = getattr(request, "_new_access_token", None)

        if new_token:
            response.set_cookie(
                key="accessToken",
                value=new_token,
                httponly=True,
                secure=True,
                samesite="Lax" if IS_DEBUG else "None",
                path="/",
            )

        print("Response processed, new token set:", bool(new_token))

        return response