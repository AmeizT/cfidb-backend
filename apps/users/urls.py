from apps.users.views import (
    UserView, 
    CreateUserView, 
    RetrieveUserView,
    CustomTokenObtainPairView
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
router.register(r'auth/signup', UserView, basename="users")
router.register(r'auth/user', RetrieveUserView, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls', namespace='restframework')),
    # path('auth/signup/', CreateUserView.as_view(), name='create_user_account'),
    path('auth/session/', CustomTokenObtainPairView.as_view(), name='session_token'),
    path('auth/session/refresh/', TokenRefreshView.as_view(), name='session_refresh'),
    path('auth/session/verify/', TokenVerifyView.as_view(), name='session_verify'),
]
