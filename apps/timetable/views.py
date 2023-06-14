from django.shortcuts import render
from apps.timetable.models import Timetable
from rest_framework import viewsets, permissions
from apps.timetable.serializers import TimetableSerializer

class TimetableView(viewsets.ModelViewSet):
    queryset = Timetable.objects.all()
    serializer_class = TimetableSerializer
    permission_classes = [permissions.AllowAny]
