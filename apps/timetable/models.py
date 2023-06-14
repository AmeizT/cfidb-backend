from django.db import models

class Timetable(models.Model):
    title = models.CharField(
        max_length=255
    )
    theme = models.CharField(
        max_length=255,
        blank=True
    )
    week_start = models.DateField()
    week_end = models.DateField() 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'timetable'
        verbose_name_plural = 'timetables'
        ordering = ['week_start']
        
    def __str__(self):
        return f'{self.week_start}'
