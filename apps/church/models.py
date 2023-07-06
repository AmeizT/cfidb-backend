import os
import uuid
import pytz
from PIL import Image
from django.db import models
from apps.users.models import User
from django.utils.translation import gettext_lazy as _


class Church(models.Model):
    pastor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pastor',
        null=True,
        blank=True
    )
    church_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)
    desc = models.TextField(blank=True)
    address = models.TextField(blank=True)
    town = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=3, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'church'
        verbose_name_plural = 'churches'
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
  


    
    

    


  
  

 
    
    

    
    








        
        


        

    
    
