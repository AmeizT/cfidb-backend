from django.db import models

class Ouestion(models.Model):
    name = models.CharField
    
    
    def __str__(self):
        return self.name


