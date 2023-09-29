from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('cfidb/admin/', admin.site.urls),
    path('api/', include('apps.bookkeeper.urls')),
    path('api/', include('apps.chat.urls')),
    path('api/', include('apps.churches.urls')),
    path('api/', include('apps.events.urls')),
    path('', include('apps.home.urls')),
    path('api/', include('apps.people.urls')),
    path('api/', include('apps.posts.urls')),
    path('api/', include('apps.projects.urls')),
    path('api/', include('apps.resources.urls')),
    path('api/', include('apps.strategy.urls')),
    path('api/', include('apps.users.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

