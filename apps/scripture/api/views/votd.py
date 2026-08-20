# VOTD - Verse of the Day

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView
from apps.scripture.services import get_verse_of_the_day


class VerseOfTheDayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        verse = get_verse_of_the_day(timezone.localdate())

        if verse is None:
            return Response(
                {"detail": "The verse of the day is temporarily unavailable."},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(verse)