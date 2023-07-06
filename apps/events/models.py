import pytz
from PIL import Image
from decimal import Decimal
from django.db import models
from datetime import datetime
from django.utils import timezone
from apps.church.models import Church
from django.utils.text import slugify
from django.utils.timezone import make_aware
from apps.events.utils import event_images_url
from apscheduler.schedulers.background import BackgroundScheduler

class Event(models.Model):
    EVENT_MODE_CHOICES = (
        ('in-person', 'In Person'),
        ('virtual', 'Virtual'),
    )
    
    EVENT_PLATFORM_CHOICES = (
        ('facebook', 'Facebook'),
        ('meet', 'Google Meet'),
        ('teams', 'Microsoft Teams'),
        ('telegram', 'Telegram'),
        ('youtube', 'YouTube'),
        ('zoom', 'Zoom'),
    )
    
    EVENT_ACCESS_CHOICES = (
        ('free', 'Free'),
        ('paid', 'Paid'),
    )
    
    host = models.ForeignKey(
        Church, 
        related_name='host', 
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    desc = models.TextField()
    date_start = models.DateField()
    date_end = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    mode = models.CharField(
        max_length=255, 
        choices=EVENT_MODE_CHOICES, 
        default='in-person', 
        blank=True
    )
    platform = models.CharField(
        max_length=255, 
        choices=EVENT_PLATFORM_CHOICES, 
        blank=True
    )
    venue = models.CharField(max_length=255)
    access = models.CharField(
        max_length=4, 
        choices=EVENT_ACCESS_CHOICES,
        default='free',
        blank=True
    )
    entrance_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    banner = models.ImageField(
        default='events/ballons.webp', 
        upload_to=event_images_url, 
        blank=True
    )
    slug = models.SlugField(
        max_length=255,
        unique=True, 
        blank=True
    )
    has_ended = models.BooleanField(default=False)
    has_started = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "event"
        verbose_name_plural = "events"
        ordering = ["-createdAt"]

    def save(self, *args, **kwargs):                
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Event.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
        
        try:
            img = Image.open(self.banner.path)
            if img.height > 800 or img.width > 1200:
                output_size = (1200, 800)
                img.thumbnail(output_size)
                img.save(self.banner.path)
        except (FileNotFoundError, OSError) as e:
            print(f"An error occurred: {e}")
        
        # Check if event has expired
        now = timezone.now()
        start_aware = make_aware(datetime.combine(self.date_start, self.time_start))
        end_aware = make_aware(datetime.combine(self.date_end, self.time_end))
                
        if end_aware <= now:
            self.has_ended = True
            self.has_started = False
        elif start_aware <= now and now < end_aware:
            self.has_ended = False
            self.has_started = True
        else:
            self.has_started = False
            
        super().save(*args, **kwargs)
            
    def __str__(self):
        return self.title
    
       
scheduler = BackgroundScheduler()
scheduler.start()


def update_expired_events():
    now = datetime.now()
    now = timezone.localtime(timezone.now(), timezone=pytz.timezone('Africa/Harare'))
    events = Event.objects.filter(has_ended=False)

    for event in events:
        start_aware = make_aware(datetime.combine(event.date_start, event.time_start))
        end_aware = make_aware(datetime.combine(event.date_end, event.time_end))

        if end_aware <= now:
            event.has_ended = True
            event.has_started = False
            print("has ended")
        elif start_aware <= now and now < end_aware:
            event.has_ended = False
            event.has_started = True
            print("has started")
        else:
            event.has_started = False
            event.has_ended = False
        
        event.save()
            

scheduler.add_job(
    update_expired_events,
    'interval',
    id="update_expired_events",
    jobstore="default",
    minutes=1,
    replace_existing=True
)