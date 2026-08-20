from django.urls import path

from apps.scripture.api.views import VerseOfTheDayView

urlpatterns = [
    path(
        "votd/",
        VerseOfTheDayView.as_view(),
        name="verse-of-the-day",
    ),
]