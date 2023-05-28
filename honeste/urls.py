from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('honeste-admin/', admin.site.urls),
    # path('', include("apps.home.urls")),
    path('api/', include("apps.users.urls")),
    path('api/', include("apps.church.urls")),
    path('api/', include("apps.chat.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

