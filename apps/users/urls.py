from apps.users.views import (
    AuthHistoryView,
    CreateUserView, 
    CustomTokenObtainPairView,
    RetrieveUserView,
    CreateUserView, 
    UniqueUserCheckView, 
    UserView,
    ListUsersView,
    AssemblyAdminView,
    check_email
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
router.register(r'auth/user-church', UserView, basename='user_church')
router.register(r'auth/user_update', UserView, basename='user_update')
router.register(r'auth/signup', CreateUserView, basename='signup')
router.register(r'auth/user', UserView, basename='user')
router.register(r'auth/user_auth_history', AuthHistoryView, basename='auth_history')
router.register(r'auth/check-unique-user', UniqueUserCheckView, basename='check_user')
router.register(r'users', ListUsersView, basename='users')
router.register(r'assembly_admins', AssemblyAdminView, basename='assembly_admins')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path("auth/check-email/", check_email, name="check_email"),
    # path('auth/', include('rest_framework.urls', namespace='restframework')),
    # path('auth/tokens/', CustomTokenObtainPairView.as_view(), name='session_token'),
    # path('auth/tokens/refresh/', TokenRefreshView.as_view(), name='session_refresh'), # type: ignore
    # path('auth/tokens/verify/', TokenVerifyView.as_view(), name='session_verify'),
]
