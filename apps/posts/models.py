from django.db import models
from django.utils import timezone
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill, SmartResize
from apps.posts.utils import post_images_path, post_image_url
from nanoid import generate # type: ignore

class Post(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='author'
    )
    assembly = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name='post_assembly'
    )
    title = models.CharField(
        max_length=255, 
        blank=True,
    )
    content = models.TextField(blank=True)
    image = models.ImageField(
        upload_to=post_image_url, 
        null=True, 
        blank=True
    )
    likes = models.ManyToManyField(
        User, 
        related_name='liked_posts',  
        blank=True
    )
    views = models.PositiveIntegerField(default=0) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Status(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        DRAFT = "draft", "Draft"

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PUBLIC,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'posts'
        ordering = ['-created_at']
         
    def __str__(self):
        return f"{self.title or 'Untitled'} by {self.author}"
    
    def increase_views(self):
        self.views += 1
            
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title or generate(size=6))
            slug_date = timezone.now().strftime('%Y-%m-%d')
            slug = f"{slug_date}-{base_slug}"
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{slug_date}-{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)
    
class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = ProcessedImageField(
        upload_to=post_images_path,
        # processors=[SmartResize(width=1080, height=1350)],
        format='WEBP',
        options={'quality': 100}
    )
    alt = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alternative text for accessibility and SEO."
    )
    caption = models.TextField(
        blank=True,
        help_text="Optional caption for the image."
    )

    class Meta:
        verbose_name = 'Post Image'
        verbose_name_plural = 'Post Images'

    def __str__(self):
        return f"Image {self.id} for post: {self.post.title}"

    def __repr__(self):
        return f"<PostImage id={self.id} post={self.post_id}>"
 
 
class Comment(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='comment_author'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    class Meta:
        verbose_name = 'comment'
        verbose_name_plural = 'comments'
        ordering = ["-created_at"]
        unique_together = ('post', 'author')
        
        
    def __str__(self):
        return self.post.assembly.name
   
    
class Like(models.Model): 
    post = models.ForeignKey(
        Post, 
        related_name='post_likes', 
        on_delete=models.CASCADE
    )
    liker = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='liker'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'like'
        verbose_name_plural = 'likes'
        unique_together = ('post', 'liker',)
        
        
    def __str__(self):
        return self.post.title
