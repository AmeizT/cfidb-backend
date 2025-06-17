import uuid
from PIL import Image
from django.db import models
from apps.users.models import User
from apps.churches.utils import church_images_path, generate_oklch_color
from django.utils.translation import gettext_lazy as _

class ChurchStatus(models.TextChoices):
    OPEN = 'Open', 'Open'
    CLOSED = 'Closed', 'Closed'

class Church(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    assigned_pastors = models.ManyToManyField(
        User,
        related_name='pastor_of',
        blank=True, 
    )
    name = models.CharField(
        max_length=100, 
        unique=True
    )
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=3, blank=True)
    language = models.CharField(max_length=12, blank=True)
    currency = models.CharField(max_length=12, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(
        upload_to=church_images_path, 
        blank=True
    )
    avatar_fallback = models.CharField(
        max_length=36, 
        blank=True
    )
    status = models.CharField(
        max_length=10,
        blank=True,
        choices=ChurchStatus.choices, 
        default=ChurchStatus.OPEN, 
    )
    cover_image = models.ImageField(
        upload_to=church_images_path,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'church'
        verbose_name_plural = 'churches'
        ordering = ['name']
        
    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()
    
    @property
    def total_members(self):
        members_count = self.members.count() 
        minors_count = self.kindred.count()   
        return members_count + minors_count
    

    def save(self, *args, **kwargs):
        """
        Override save method to automatically generate 
        an OKLCH color if avatar_fallback is blank
        """
        if not self.avatar_fallback:
            self.avatar_fallback = generate_oklch_color()
        
        super().save(*args, **kwargs)

    
class ImageUpload(models.Model):
    name = models.CharField(max_length=255, blank=True)
    image = models.FileField(
        upload_to="server_action/", 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'image upload'
        verbose_name_plural = 'image upload'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
  


    
    

    


  
  

 
    
    

    
    








        
        


        

    
    
