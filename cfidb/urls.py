import os
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static

ADMIN_URL = os.getenv("ADMIN_URL")

urlpatterns = [
    path('portal-a26e12/', admin.site.urls),
    path("api/v1/", include("apps.examinations.urls")),

    path('api/v1/', include([
        path('auth/', include('apps.users.urls')),
        path('analyzer/', include('apps.analyzer.urls')),
        path('churches/', include('apps.churches.urls'), name="churches"),
        path('regions/', include('apps.churches.regional_urls'), name="regions"),
        path('people/', include('apps.people.urls'), name="people"),
        path('bookkeeper/', include('apps.bookkeeper.urls'), name="bookkeeper"),
        path('reports/', include('apps.reports.urls'), name="reports"),
        path('posts/', include('apps.posts.urls')),
        path('core/', include('apps.core.urls')),
        path('jethro/', include('apps.jethro.urls')),
        path('scripture/', include('apps.scripture.api.urls')),
    ])),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
