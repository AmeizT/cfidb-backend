from apps.users.views import (
    AccountView,
    CreateUserView, 
    CustomTokenObtainPairView,
    RetrieveUserView,
    CreateUserView, 
    UniqueUserCheckView, 
    UserView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from django.urls import path, include
from rest_framework import urlpatterns
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'auth/user-church', UserView, basename="user_church")
router.register(r'auth/signup', CreateUserView, basename="signup")
router.register(r'auth/user', RetrieveUserView, basename='user')
router.register(r'auth/account', AccountView, basename="account")
router.register(r'auth/check-unique-user', UniqueUserCheckView, basename='check_user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    # path('auth/', include('rest_framework.urls', namespace='restframework')),
    # path('auth/tokens/', CustomTokenObtainPairView.as_view(), name='session_token'),
    # path('auth/tokens/refresh/', TokenRefreshView.as_view(), name='session_refresh'), # type: ignore
    # path('auth/tokens/verify/', TokenVerifyView.as_view(), name='session_verify'),
]
