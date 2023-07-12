from decimal import Decimal
from django.db import models
from apps.churches.models import Church
from django.core.validators import RegexValidator
from django.forms import ValidationError

class Attendance(models.Model):
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
        return f'{self.church}'


class Homecell(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='homecell'
    )
    title = models.CharField(
        max_length=255
    )
    description = models.TextField(
        blank=True
    )
    leader = models.CharField(
        max_length=255,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Home Cell'
        verbose_name_plural = 'Home Cells'
        ordering = ["-created_at"]
        
    def __str__(self):
        return f'{self.title}'
    
     
class HCAttendance(models.Model):
    church = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        related_name='hc_church'
    )
    homecell = models.ForeignKey(
        Homecell,
        on_delete=models.CASCADE,
        related_name='hc_attendance',
        null=True
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField() 
    venue = models.CharField(
        max_length=255
    )
    attendance = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    new = models.BigIntegerField(default=0)
    repented = models.BigIntegerField(default=0)
    activities = models.TextField(blank=True)
    achievements = models.TextField(blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Home Cell Attendance'
        verbose_name_plural = 'Home Cell Attendance'
        ordering = ["-created_at"]
        
    def __str__(self):
        return f'{self.homecell}'
    

class Members(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )
    
    RELATIONSHIP_CHOICES = (
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
        ('Separated', 'Separated'),
        ('Engaged', 'Engaged'),
        ('In a Relationship', 'In a Relationship'),
        ('Domestic Partnership', 'Domestic Partnership'),
        ('Civil Union', 'Civil Union'),
        ('Committed', 'Committed'),
        ('Common-Law Marriage', 'Common-Law Marriage'),
        ('Traditional Marriage', 'Traditional Marriage'),
        ('Co-parenting', 'Co-parenting'),
    )

    PREFIX_CHOICES = (
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Mrs', 'Mrs'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    )
    
    CHURCH_POSITIONS_CHOICES = [
        ('Sunday School Teacher', 'Sunday School Teacher'),
        ('Youth Leader', 'Youth Leader'),
        ('Deacon', 'Deacon'),
        ('Deaconess', 'Deaconess'),
        ('Elder', 'Elder'),
        ('Praise and Worship Director', 'Praise and Worship Director'),
        ('Pastor', 'Pastor'),
        ('Senior Pastor', 'Senior Pastor'),
        ('Overseer', 'Overseer'),
        ('President', 'President'),
        ('Media Director', 'Media Director'),
        ('WOE Leader', 'WOE Leader'),
        ('Gatekeepers Leader', 'Gatekeepers Leader'),
        ('House Keeper', 'House Keeper'),
        ('Home Cell Leader', 'Home Cell Leader'),
        ('Secretary', 'Secretary'),
        ('Treasurer', 'Treasurer'),
        ('Other', 'Other'),
    ]

    MINISTRY_CHOICES = [
        ('Administration', 'Administration'),
        ('Christian education', 'Christian education'),
        ('Counseling', 'Counseling'),
        ('Discernment', 'Discernment'),
        ('Evangelism', 'Evangelism'),
        ('Giving', 'Giving'),
        ('Hospitality', 'Hospitality'),
        ('Intercession', 'Intercession'),
        ('Leadership', 'Leadership'),
        ('Media and Communications', 'Media and Communications'),
        ('Other', 'Other'),
        ('Praise and Worship', 'Praise and Worship'),
        ('Ushering', 'Ushering'),
    ]

    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE,
        related_name='members'
    )
    prefix = models.CharField(
        max_length=255, 
        choices=PREFIX_CHOICES,
        blank=True
    )
    first_name = models.CharField(max_length=255)
    other_names = models.CharField(
        max_length=255, 
        blank=True
    )
    last_name = models.CharField(max_length=255)
    dob = models.DateField()
    gender = models.CharField(
        max_length=255, 
        choices=GENDER_CHOICES
    )
    relationship = models.CharField(
        max_length=255, 
        blank=True,
        choices=RELATIONSHIP_CHOICES
    )
    occupation = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=255)
    phone = models.CharField(max_length=24, blank=True)
    email = models.EmailField(blank=True)
    membersince = models.DateField()
    baptism_date = models.DateField(blank=True)
    tithes = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    ministry = models.CharField(
        max_length=255, 
        blank=True,
        choices=MINISTRY_CHOICES
    )
    position = models.CharField(
        max_length=255, 
        blank=True,
        choices=CHURCH_POSITIONS_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name']
        verbose_name = 'member'
        verbose_name_plural = 'members'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    
    def save(self, *args, **kwargs):
        # Check for duplicate entries
        if Members.objects.filter(
            first_name=self.first_name,
            last_name=self.last_name,
            dob=self.dob,
            phone=self.phone).exists():
            raise ValidationError(
                "A member with the same name, date of birth, and phone number already exists."
            )
        
        # Save the member if no duplicate entries found
        super(Members, self).save(*args, **kwargs)
    
    