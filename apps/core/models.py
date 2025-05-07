from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.users.models import User
from django.utils.text import slugify
from imagekit.models import ProcessedImageField
from apps.core.choices import BlogCategoryChoices, BlogStatusChoices
from apps.core.utils import blog_image_url



class TermsAndConditions(models.Model):
    title = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=10, default="1.0")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            last_version = TermsAndConditions.objects.order_by('-created_at').first()
            if last_version:
                major, minor = map(int, last_version.version.split('.'))
                minor += 1
                self.version = f"{major}.{minor}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Terms v{self.version}"

class UserTermsAcceptance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    terms = models.ForeignKey(TermsAndConditions, on_delete=models.CASCADE)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'terms')

    def __str__(self):
        return f"{self.user} accepted {self.terms.version} on {self.accepted_at}"
    

class Blog(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='blog_post_author'
    )
    title = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True)
    body = models.TextField()
    category = models.CharField(
        max_length=255,
        choices=BlogCategoryChoices.choices, 
        default=BlogCategoryChoices.GENERAL, 
    )
    image = ProcessedImageField(
        blank=True,
        null=True,
        upload_to=blog_image_url,
        # processors=[SmartResize(width=1080, height=1350)],
        format='WEBP', 
        options={'quality': 80} 
    )
    views = models.PositiveIntegerField(default=0) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    read_by = models.ManyToManyField(
        User, 
        related_name='blog_post_views',  
        blank=True
    )
    status = models.CharField(
        max_length=255,
        choices=BlogStatusChoices.choices, 
        default=BlogStatusChoices.PUBLISHED, 
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'blog'
        verbose_name_plural = 'blog'
        ordering = ['-created_at']
    
    def increase_views(self):
        self.views += 1
            
    def save(self, *args, **kwargs): 
        self.increase_views() 

        if not self.slug:
            base_slug = slugify(self.title)
            slug_date = (
                self.created_at.strftime('%Y-%m-%d') if self.created_at else timezone.now().strftime('%Y-%m-%d')
            )
            self.slug = f"{base_slug}"
            counter = 1
            
            while Blog.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
         
    def __str__(self):
        return self.title
         

class DocumentationCategory(models.TextChoices):
    GENERAL = "General", "General"
    API = "API", "API"
    USER_GUIDE = "User Guide", "User Guide"
    TECHNICAL = "Technical", "Technical"

class DocumentationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"

class Documentation(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='documentation_posts'
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=DocumentationCategory.choices,
        default=DocumentationCategory.GENERAL,
    )
    status = models.CharField(
        max_length=50,
        choices=DocumentationStatus.choices,
        default=DocumentationStatus.PUBLISHED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Documentation"
        verbose_name_plural = "Documentation"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


   
    

