from django.db import models
from datetime import timedelta
from django.utils import timezone
from django.utils.text import slugify
from nanoid import generate # type: ignore
from apps.announcements.choices.platform import PlatformChoices

class AnnouncementQuerySet(models.QuerySet):
    def active(self):
        now = timezone.now()
        return self.filter(
            expires_at__gt=now,
            publish_at__lte=now 
        )

class Announcement(models.Model):
    reference = models.CharField(max_length=50, unique=True, default=generate(size=12))
    title = models.CharField(max_length=255)
    message = models.TextField()
    platform = models.CharField(
        max_length=20,
        choices=PlatformChoices.choices,
        default=PlatformChoices.DATABASE
    )
    read_more_url = models.URLField(blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True)
    publish_at = models.DateTimeField(default=timezone.now)
    objects = AnnouncementQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate(size=12)

        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)

        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}"
            counter = 1
            
            while Announcement.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at