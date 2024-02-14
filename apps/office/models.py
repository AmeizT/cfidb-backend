from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from apps.office.abstract import AbstractBaseDocument
from apps.office.utils import meeting_file_path, uploaded_circular_path, uploaded_strategy_path
from apps.office.choices import (
    DocumentCategoryChoices, 
    MeetingAttendanceChoices,
    MeetingCategoryChoices, 
    MeetingPlatformChoices,
    StrategyStatusChoices, 
)

class Meeting(models.Model):
    assembly = models.ForeignKey(
        Church, 
        related_name='meeting_assembly',
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=255)
    mode = models.CharField(
        max_length=255, 
        choices=MeetingAttendanceChoices.choices, 
        default=MeetingAttendanceChoices.PERSON, 
        blank=True
    )
    platform = models.CharField(
        max_length=255, 
        choices=MeetingPlatformChoices.choices, 
        default=MeetingPlatformChoices.ZOOM,
        blank=True
    )
    category = models.CharField(
        max_length=255, 
        blank=True,
        choices=MeetingCategoryChoices.choices,
    )
    meeting_thumbnail_fallback = models.CharField(max_length=255, blank=True)
    meeting_start_time = models.DateTimeField()
    meeting_end_time = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        related_name='meeting_created_by',
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'meeting'
        verbose_name_plural = 'meetings'
        ordering = ['-created_at']
             
    def __str__(self):
        return f'{self.title}'


class Minutes(models.Model):
    assembly = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='assembly_minutes'
    )
    meeting = models.ForeignKey(
        Meeting,
        on_delete=models.CASCADE,
        related_name='meeting'
    )
    uploaded_file = models.FileField(
        upload_to=meeting_file_path, 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'minute'
        verbose_name_plural = 'minutes'
        ordering = ['-created_at']
             
    def __str__(self):
        return f'{self.meeting.title}'


class Strategy(AbstractBaseDocument):
    uploaded_document = models.FileField(
        upload_to=uploaded_strategy_path,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=255, 
        blank=True,
        choices=StrategyStatusChoices.choices,
        default=StrategyStatusChoices.PENDING,
    )
    remarks = models.TextField(blank=True)
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        related_name='strategy_moderator',
        blank=True, 
        null=True
    )
    assembly = models.ForeignKey(
        Church,
        on_delete=models.CASCADE, 
        related_name='assembly_strategy',
    )
    
    class Meta:
        verbose_name = 'strategy'
        verbose_name_plural = 'strategies'
        ordering = ['-created_at']
        

class Circular(AbstractBaseDocument):
    uploaded_document = models.FileField(
        upload_to=uploaded_circular_path,
        null=True,
        blank=True
    )
    category = models.CharField(
        max_length=255, 
        blank=True,
        choices=DocumentCategoryChoices.choices,
    )
    
    class Meta:
        verbose_name = 'Circular'
        verbose_name_plural = 'Circulars'
        ordering = ['-created_at']
        
