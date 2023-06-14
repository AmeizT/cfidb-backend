from django.db import models
from apps.timetable.models import Timetable
from apps.church.models import Church

class Attendance(models.Model):
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.CASCADE,
        related_name='register'
    )
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='attendance'
    ) 
    sunday = models.BigIntegerField(default=0)
    home = models.BigIntegerField(default=0)
    friday = models.BigIntegerField(default=0)
    outreach = models.BigIntegerField(default=0)
    kids = models.BigIntegerField(default=0)
    adults = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    new = models.BigIntegerField(default=0)
    baptized = models.BigIntegerField(default=0)
    repented = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'attendance'
        verbose_name_plural = 'attendance'
        ordering = ["-created_at"]
        
    def __str__(self):
        return f'{self.timetable}'
    
    
class Members(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Not Known', 'Not Known'),
    )
    
    RELATIONSHIP_CHOICES = (
        ('Married', 'Married'),
        ('Single', 'Single'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
        ('Separated', 'Separated'),
        ('None', 'None'),
    )
    
    TITLE_CHOICES = (
        ('Mr', 'Mr.'),
        ('Ms', 'Ms.'),
        ('Mrs', 'Mrs.'),
        ('Dr', 'Dr.'),
        ('Prof', 'Prof.'),
    )
    
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='member'
    )
    first_name = models.CharField(max_length=255)
    other_names = models.CharField(
        max_length=255, 
        blank=True
    )
    surname = models.CharField(max_length=255)
    title = models.CharField(
        max_length=255, 
        choices=TITLE_CHOICES
    )
    dob = models.DateField()
    date_of_baptism = models.DateField(blank=True)
    gender = models.CharField(
        max_length=255, 
        choices=GENDER_CHOICES
    )
    relationship = models.CharField(
        max_length=255, 
        blank=True,
        choices=RELATIONSHIP_CHOICES
    )
    address = models.TextField(blank=True)
    country = models.CharField(max_length=255)
    work = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=24, blank=True)
    email = models.EmailField(blank=True)
    membersince = models.DateField()
    ministry = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['surname']
        verbose_name = 'member'
        verbose_name_plural = 'members'

    def __str__(self):
        return f'{self.first_name} {self.surname}'
    