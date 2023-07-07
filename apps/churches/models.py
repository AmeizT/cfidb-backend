import os
import uuid
import pytz
from PIL import Image
from django.db import models
from apps.users.models import User
from django.utils.translation import gettext_lazy as _


class Church(models.Model):
    church_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=3, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=20, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'church'
        verbose_name_plural = 'churches'
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
  


    
    

    


  
  

 
    
    

    
    








        
        


        

    
    
