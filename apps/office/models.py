from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from apps.office.utils import meeting_file_path, document_path
from apps.office.choices import DocumentCategoryChoices, MeetingCategoryChoices, StatusChoices

class MeetingChoices(models.TextChoices):
    BANK = 'Bank', 'Bank'
    CASH = 'Cash', 'Cash'
    CHEQUE = 'Cheque', 'Cheque'
    EFT = 'EFT', 'EFT'
    OTHER = 'Other', 'Other'


def strategy_file_path(instance, filename):
    return 'cfidb/document/{0}/{1}/{2}'.format(
        instance.branch.name,  
        instance.category,  
        filename
    )


class Meeting(models.Model):
    MEETING_MODE_CHOICES = (
        ('in-person', 'In Person'),
        ('virtual', 'Virtual'),
    )
    
    MEETING_PLATFORM_CHOICES = (
        ('facebook', 'Facebook'),
        ('meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
        ('telegram', 'Telegram'),
        ('whatsapp', 'WhatsApp'),
        ('zoom', 'Zoom'),
    )
    
    branch = models.ForeignKey(
        Church, 
        related_name='meeting_branch',
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=255)
    mode = models.CharField(
        max_length=255, 
        choices=MEETING_MODE_CHOICES, 
        default='in-person', 
        blank=True
    )
    platform = models.CharField(
        max_length=255, 
        choices=MEETING_PLATFORM_CHOICES, 
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
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='minutes_branch'
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


class Document(models.Model):
    branch = models.ForeignKey(
        Church,
        on_delete=models.SET_NULL, 
        related_name='document',
        blank=True, 
        null=True
    )
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    uploaded_document = models.FileField(
        upload_to=document_path,
        null=True,
        blank=True
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    category = models.CharField(
        max_length=255, 
        blank=True,
        choices=DocumentCategoryChoices.choices,
    )
    status = models.CharField(
        max_length=255, 
        blank=True,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    remarks = models.TextField(blank=True)
    document_thumbnail_fallback = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        related_name='document_creator',
        blank=True, 
        null=True
    )
    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, 
        related_name='document_moderator',
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'document'
        verbose_name_plural = 'documents'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):               
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Document.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)