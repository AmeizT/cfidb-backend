from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('honeste/master/', admin.site.urls),
    path('api/', include('apps.chat.urls')),
    path('api/', include('apps.church.urls')),
    path('api/', include('apps.demographics.urls')),
    path('api/', include('apps.events.urls')),
    path('api/', include('apps.finance.urls')),
    # path('', include('apps.home.urls')),
    path('api/', include('apps.timetable.urls')),
    path('api/', include('apps.users.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

