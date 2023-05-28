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
    desc = models.TextField(blank=True)
    address = models.TextField(blank=True)
    town = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
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
    
  
class Demographics(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='demographics'
    )
    
    title = models.CharField(
        max_length=255, 
        blank=True
    )
    week_start = models.DateField()
    week_end = models.DateField() 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'demographics'
        verbose_name_plural = 'demographics'
        ordering = ['week_start']
        
    def __str__(self):
        return f'{self.week_start}'
    
    
class Attendance(models.Model):
    period = models.ForeignKey(
        Demographics,
        on_delete=models.CASCADE,
        related_name='period'
    )
    sun_service = models.BigIntegerField(default=0)
    cell_meeting = models.BigIntegerField(default=0)
    fri_prayer = models.BigIntegerField(default=0)
    outreach = models.BigIntegerField(default=0)
    kids = models.BigIntegerField(default=0)
    adults = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    new_members = models.BigIntegerField(default=0)
    baptism = models.BigIntegerField(default=0)
    repented = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'attendance'
        verbose_name_plural = 'attendance'
        ordering = ["-created_at"]
        
    def __str__(self):
        return f'{self.period}'
    
    
class Member(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    RELATIONSHIP_CHOICES = (
        ('M', 'Married'),
        ('S', 'Single'),
        ('D', 'Divorced'),
        ('W', 'Widowed'),
        ('SP', 'Separated'),
        ('N', 'None'),
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
    name = models.CharField(max_length=255)
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
        max_length=1, 
        choices=GENDER_CHOICES
    )
    relationship = models.CharField(
        max_length=2, 
        blank=True,
        choices=RELATIONSHIP_CHOICES
    )
    address = models.TextField(blank=True)
    country = models.CharField(max_length=255)
    work = models.CharField(max_length=255, blank=True)
    contacts = models.CharField(max_length=15, blank=True)
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
        return f'{self.name} {self.surname}'
    


  
  

 
    
    

    
    








        
        


        

    
    
