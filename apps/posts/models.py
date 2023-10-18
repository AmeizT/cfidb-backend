from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from imagekit.processors import ResizeToFill
from imagekit.models import ProcessedImageField
from apps.posts.utils import post_images_path, post_image_url


class Post(models.Model):
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='author'
    )
    branch = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name='branch'
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=post_image_url, null=True, blank=True)
    views = models.PositiveIntegerField(default=0) 
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_private = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def increase_views(self):
        self.views += 1
            
    
    def save(self, *args, **kwargs): 
        self.increase_views() 
                       
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = base_slug
            counter = 1
            while Post.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)
    
    
    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'posts'
        ordering = ['-created_at']
        
        
    def __str__(self):
        return self.branch.name
    

class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = ProcessedImageField(
        upload_to=post_images_path,
        processors=[ResizeToFill(800, 600)], # type: ignore
        format='WEBP', # type: ignore
        options={'quality': 90} # type: ignore
    )
    alt = models.CharField(
        max_length=255,
        blank=True
    )
    caption = models.CharField(
        max_length=255,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Post Image'
        verbose_name_plural = 'Post Images'
        
        
    def __str__(self):
        return self.post.title
 
 
class Comment(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE,
        related_name='comments'
    )
    comment_author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='comment_author'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    class Meta:
        verbose_name = 'comment'
        verbose_name_plural = 'comments'
        
        
    def __str__(self):
        return self.post.title
   
    
class Reaction(models.Model):
    REACTION_CHOICES = (
        ('like', 'Like'),
        ('love', 'Love'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    )
    
    post = models.ForeignKey(
        Post, 
        related_name='reactions', 
        on_delete=models.CASCADE
    )
    review_author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='review_author'
    )
    reaction = models.CharField(
        max_length=10, 
        choices=REACTION_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'reaction'
        verbose_name_plural = 'reactions'
        unique_together = ('post', 'review_author', 'reaction')
        
        
    def __str__(self):
        return self.post.title
