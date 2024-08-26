from django.db import models
from django.utils import timezone
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from imagekit.processors import ResizeToFill
from imagekit.models import ProcessedImageField
from apps.forum.helpers import changelog_image_url

class ChangelogCategory(models.TextChoices):
    ATN = 'Attendance', 'Attendance'
    AUT = 'Authentication', 'Authentication'
    CLG = "Changelog", "Changelog"
    DEM = 'Demographics', 'Demographics'
    FIN = 'Finance', 'Finance'
    GEN = 'General', 'General'
    STR = 'Strategy', 'Strategy'
    TMP = 'Templates', 'Templates'
    UPD = 'Updates', 'Updates'

class Changelog(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='changelog_post_author'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=255,
        choices=ChangelogCategory.choices, 
        default=ChangelogCategory.GEN, 
    )
    # image = ProcessedImageField(
    #     blank=True,
    #     null=True,
    #     upload_to=changelog_image_url,
    #     processors=[ResizeToFill(1080, 1080)],
    #     format='WEBP',
    #     options={'quality': 100}
    # )
    image = ProcessedImageField(
        blank=True,
        null=True,
        upload_to=changelog_image_url,
        # processors=[SmartResize(width=1080, height=1350)],
        format='WEBP', # type: ignore
        options={'quality': 80} # type: ignore
    )
    views = models.PositiveIntegerField(default=0) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    read_by = models.ManyToManyField(
        User, 
        related_name='post_views',  
        blank=True
    )
    is_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def increase_views(self):
        self.views += 1
            
    def save(self, *args, **kwargs): 
        self.increase_views() 

        if not self.slug:
            base_slug = slugify(self.title)
            slug_date = (
                self.created_at.strftime('%Y-%m-%d') if self.created_at else timezone.now().strftime('%Y-%m-%d')
            )
            self.slug = f"{slug_date}-{base_slug}"
            counter = 1
            
            while Changelog.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'changelog'
        verbose_name_plural = 'changelog'
        ordering = ['-created_at']
         
    def __str__(self):
        return self.title
         



   
    

