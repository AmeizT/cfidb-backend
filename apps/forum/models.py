from django.db import models
from django.utils import timezone
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from imagekit.processors import ResizeToFill
from imagekit.models import ProcessedImageField
from apps.forum.helpers import forum_image_path

class ForumCategory(models.TextChoices):
    ATN = 'Attendance', 'Attendance'
    AUT = 'Authentication', 'Authentication'
    CLG = "Changelog", "Changelog"
    DEM = 'Demographics', 'Demographics'
    FIN = 'Finance', 'Finance'
    GEN = 'General', 'General'
    STR = 'Strategy', 'Strategy'
    TMP = 'Templates', 'Templates'
    UPD = 'Updates', 'Updates'

class Forum(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='forum_author'
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=255,
        choices=ForumCategory.choices, 
        default=ForumCategory.GEN, 
    )
    image = ProcessedImageField(
        blank=True,
        null=True,
        upload_to=forum_image_path,
        processors=[ResizeToFill(1080, 1080)],
        format='WEBP',
        options={'quality': 100}
    )
    viewCount = models.PositiveIntegerField(default=0) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def increase_views(self):
        self.viewCount += 1
            
    def save(self, *args, **kwargs): 
        self.increase_views() 

        if not self.slug:
            base_slug = slugify(self.title)
            
            # Check if created_at is not None before formatting
            slug_date = (
                self.created_at.strftime('%Y-%m-%d') if self.created_at else timezone.now().strftime('%Y-%m-%d')
            )
            
            self.slug = f"{slug_date}-{base_slug}"
            counter = 1
            
            while Forum.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'forum'
        verbose_name_plural = 'forum'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return self.title
     
class Reply(models.Model):
    discussion = models.ForeignKey(
        Forum, 
        on_delete=models.CASCADE,
        related_name='replies'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='forum_reply_author'
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    class Meta:
        verbose_name = 'reply'
        verbose_name_plural = 'replies'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return self.discussion.title
   
    

