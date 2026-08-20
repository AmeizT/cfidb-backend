from django.urls import path, include, re_path
from apps.timetable.views import TimetableView
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

router.register(r'church/timetable', TimetableView, basename='timetable')

urlpatterns = [
    path('', include(router.urls)),
]



