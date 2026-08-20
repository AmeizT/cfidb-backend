from django.db import models
from django.utils.translation import gettext_lazy as _
    
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
    
  


    
    

    


  
  

 
    
    

    
    








        
        


        

    
    
