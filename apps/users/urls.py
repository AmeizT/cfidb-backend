from django.urls import path, include
from rest_framework.routers import SimpleRouter
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.users.views import AssemblyAdminView, AuthHistoryView, CreateUserView, CustomLoginView, ListUsersView, UniqueUserCheckView, UserView, active_users, check_email, current_user, logout_view

router = SimpleRouter()

router.register(r'user-church', UserView, basename='user_church')
router.register(r'user_update', UserView, basename='user_update')
router.register(r'signup', CreateUserView, basename='signup')
router.register(r'user', UserView, basename='user')
router.register(r'user_auth_history', AuthHistoryView, basename='auth_history')
router.register(r'auth/check-unique-user', UniqueUserCheckView, basename='check_user')
router.register(r'users', ListUsersView, basename='users')
router.register(r'assembly_admins', AssemblyAdminView, basename='assembly_admins')

urlpatterns = [
    path('', include('djoser.urls')),
    path('', include('djoser.urls.jwt')),
    path('users/active/<int:church_id>/', active_users, name='active_users'),
    path("auth/check-email/", check_email, name="check_email"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path('logout/', logout_view, name='logout'),
    path('verify/', current_user, name='verify_user'),
    path(
        "schema/",
        SpectacularAPIView.as_view(
            authentication_classes=[],
            permission_classes=[AllowAny]
        ),
        name="schema",
    ),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path('', include(router.urls)),
]