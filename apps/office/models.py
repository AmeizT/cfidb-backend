from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from apps.office.utils import meeting_file_path

class MeetingChoices(models.TextChoices):
    BANK = 'Bank', 'Bank'
    CASH = 'Cash', 'Cash'
    CHEQUE = 'Cheque', 'Cheque'
    EFT = 'EFT', 'EFT'
    OTHER = 'Other', 'Other'

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
        ('youtube', 'YouTube'),
        ('zoom', 'Zoom'),
    )
    
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='meeting_branch'
    )
    title = models.CharField(max_length=255)
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
    timestamp_start = models.DateTimeField()
    timestamp_end = models.DateTimeField()
    color_id = models.CharField(max_length=255, blank=True)
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
    attachment = models.FileField(
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



def strategy_file_path(instance, filename):
    return 'cfidb/circular/{0}/{1}/{2}'.format(
        instance.branch.name,  
        instance.timestamp,  
        filename
    )

class Circular(models.Model):
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='circular_branch'
    )
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    attachment = models.FileField(
        upload_to=strategy_file_path,
        null=True,
        blank=True
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    color_id = models.CharField(max_length=255, blank=True)
    timestamp = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'circular'
        verbose_name_plural = 'circular'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Circular.objects.filter(slug=self.slug).exists():
                self.slug = f'{base_slug}-{counter}'
                counter += 1

        super().save(*args, **kwargs)
