from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static


urlpatterns = [
    path('portal-a26e12/', admin.site.urls),
    path('', include('apps.home.urls')),
    path('api/v1/', include('apps.analyzer.urls')),
    path('api/v1/', include('apps.announcements.urls')),
    path('api/v1/', include('apps.bookkeeper.urls')),
    path('api/v1/', include('apps.chat.urls')),
    path('api/v1/', include('apps.churches.urls')),
    path('api/v1/', include('apps.events.urls')),
    path('api/v1/', include('apps.forum.urls')),
    path('api/v1/', include('apps.integrations.urls')),
    path('api/v1/', include('apps.office.urls')),
    path('api/v1/', include('apps.people.urls')),
    path('api/v1/', include('apps.posts.urls')),
    path('api/v1/', include('apps.reports.urls')),
    path('api/v1/', include('apps.resources.urls')),
    path('api/v1/', include('apps.strategic.urls')),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.core.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

