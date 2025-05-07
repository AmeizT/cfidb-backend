import uuid
from nanoid import generate # type: ignore
from enum import Enum
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.people.utils import member_avatar_url
from django.contrib.auth.hashers import make_password, check_password
from apps.users.models import User
from datetime import date, datetime
from django.utils.text import slugify
from apps.churches.models import Church
from django.forms import ValidationError
from django.core.validators import RegexValidator
from imagekit.processors import ResizeToFill, SmartResize
from imagekit.models import ProcessedImageField
from apps.people.choices import (
    AttendanceCategories,
    ChurchRoles,
    EducationLevel,
    Gender, 
    GuardianRelationship,
    MembershipStatus,
    Ministries, 
    Prefixes, 
    Relationship,
)

class Ministry(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Ministry"
        verbose_name_plural = "Ministries"
    
    def __str__(self):
        return self.name

class Position(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

def generate_member_key():
    generate(size=12) 

class Member(models.Model):
    assembly = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name="members"
    )
    member_key = models.CharField(
        default=generate_member_key,
        max_length=21,
        unique=True,
        editable=False,
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="editor", 
        blank=True, 
        null=True
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="updated_members",
        blank=True,
        null=True
    )
    prefix = models.CharField(
        max_length=26, 
        choices=Prefixes.choices, 
        blank=True
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(
        max_length=100, 
        blank=True
    )
    maiden_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=100, blank=True)
    gender = models.CharField(
        max_length=255, 
        choices=Gender.choices
    )
    relationship = models.CharField(
        max_length=255, 
        blank=True, 
        choices=Relationship.choices
    )
    marriage_date = models.DateField(null=True, blank=True)
    spouse = models.ForeignKey(  
        'self',
        on_delete=models.SET_NULL,
        related_name='spouse_of',
        null=True,
        blank=True
    )
    phone_number = models.CharField(
        max_length=24, 
        blank=True
    )
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17, 
        blank=True
    )
    secondary_phone_number = models.CharField( 
        validators=[phone_regex],
        max_length=17,
        blank=True
    )
    email = models.EmailField(blank=True)
    address = models.CharField(
        max_length=255,
        blank=True
    )
    address_line2 = models.CharField(
        max_length=255,
        blank=True
    )
    city = models.CharField(
        max_length=255, 
        blank=True
    )
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=255)
    membersince = models.DateField(
        null=True,
        blank=True,
        default=date(1900, 1, 1),
    )
    membership_status = models.CharField(
        max_length=255, 
        blank=True,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ESTABLISHED
    )
    previous_church = models.CharField( 
        max_length=255,
        blank=True
    )
    ministries = models.ManyToManyField(Ministry, blank=True)
    positions = models.ManyToManyField(Position, blank=True)
    baptized = models.BooleanField(default=False)
    baptized_at = models.DateField(
        blank=True,
        null=True,
        default=date(1900, 1, 1),
    )
    baptized_where = models.CharField(max_length=255, blank=True) 
    confirmation_date = models.DateField(null=True, blank=True)
    occupation = models.CharField(max_length=255, blank=True)
    employer = models.CharField(max_length=255, blank=True) 
    education_level = models.CharField( 
        max_length=100,
        blank=True,
        choices=EducationLevel.choices
    )
    skills = models.CharField(max_length=255, blank=True)  
    emergency_contact_name = models.CharField(max_length=255, blank=True) 
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True
    ) 
    avatar = ProcessedImageField(
        upload_to=member_avatar_url,
        processors=[SmartResize(width=800, height=800)],
        format='WEBP', 
        options={'quality': 80},
        blank=True,
        null=True,
    )
    avatar_fallback = models.CharField(
        max_length=24, 
        blank=True
    )
    access_pin = models.CharField(max_length=128, blank=True)
    pin_set = models.BooleanField(default=False)

    def set_access_pin(self, raw_pin):
        self.access_pin = make_password(raw_pin)
        self.pin_set = True
        self.save()

    def verify_access_pin(self, raw_pin):
        return check_password(raw_pin, self.access_pin)
    
    notes = models.TextField(blank=True)  
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Member"
        verbose_name_plural = "Members"
        indexes = [
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['email']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['membership_status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['first_name', 'last_name', 'date_of_birth', 'phone_number'],
                name='unique_member_keyentity'
            )
        ]

    @property
    def full_name(self):
        """Return the member's full name."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)
    
    @property
    def age(self):
        """Calculate the member's age."""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def clean(self):
        """Validate the model before saving."""
        # Ensure baptized_at is set only if baptized is True
        # if not self.baptized and self.baptized_at:
        #     raise ValidationError({"baptized_at": "Baptism date cannot be set if member is not baptized."})
        
        # Ensure marriage_date is set only for married members
        if self.relationship != Relationship.MARRIED and self.marriage_date:
            raise ValidationError({"marriage_date": "Marriage date cannot be set if member is not married."})

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.member_key}"

    def save(self, *args, **kwargs):
        if not self.member_key:
            self.member_key = generate()

        # if self.pk is None:
        #     if Member.objects.filter(
        #         first_name=self.first_name,
        #         last_name=self.last_name,
        #         date_of_birth=self.date_of_birth,
        #         phone_number=self.phone_number,
        #     ).exists():
        #         raise ValidationError(
        #             "A member with the same name, date of birth, and phone number already exists."
        #         )
        super(Member, self).save(*args, **kwargs)
        
                
class JuniorMember(models.Model):
    # member_key = models.UUIDField(
    #     default=uuid.uuid4, 
    #     editable=False, 
    #     unique=True
    # )
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name="kindred"
    )
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(
        max_length=255, 
        blank=True
    )
    last_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    gender = models.CharField(
        max_length=255, 
        choices=Gender.choices
    )
    guardian = models.ForeignKey(
        Member,
        on_delete=models.SET_NULL, 
        related_name="guardian",
        blank=True, 
        null=True
    )
    guardian_relationship = models.CharField(
        max_length=255, 
        blank=True, 
        choices=GuardianRelationship.choices
    )
    membersince = models.DateField()
    membership_status = models.CharField(
        max_length=255, 
        blank=True,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ESTABLISHED
    )
    baptized_at = models.DateField(
        blank=True,
        null=True,
        default=date(1900, 1, 1)
    )
    avatar_fallback = models.CharField(
        max_length=24, 
        blank=True
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="kindred_editor", 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Junior Member"
        verbose_name_plural = "Junior Members"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            if JuniorMember.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth,
            ).exists():
                raise ValidationError(
                    "A member with the same name, date of birth, and phone_number number already exists."
                )
        super(JuniorMember, self).save(*args, **kwargs)
        
 
class Tally(models.Model):
    branch = models.ForeignKey(
        Church,
        on_delete=models.CASCADE, 
        related_name="tally_branch"
    )
    members = models.ManyToManyField(Member, blank=True)
    category = models.CharField(
        max_length=24, 
        blank=True, 
        choices=AttendanceCategories.choices,
        default=AttendanceCategories.SUNDAY
    )
    timestamp = models.DateTimeField(
        null=True, 
        blank=True, 
        default=datetime(1900, 1, 1, 0, 0, 0)
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="tally_editor", 
        blank=True, 
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tally"
        verbose_name_plural = "tallies"
        ordering = ["-timestamp"]
        

    def __str__(self):
        return f"{self.branch.name}"
 
                         
class Homecell(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.PROTECT, related_name="homecell"
    )
    group_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(Member, blank=True)
    non_church_members = models.TextField(blank=True)
    leader = models.ForeignKey(
        Member, 
        on_delete=models.SET_NULL, 
        related_name="homecell_leader", 
        blank=True, 
        null=True
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "homecell"
        verbose_name_plural = "homecells"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.group_name}"
    

class Attendance(models.Model):
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name="attendance"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="attendance_editor", 
        blank=True, 
        null=True
    )
    homecell = models.ForeignKey(
        Homecell, 
        on_delete=models.SET_NULL, 
        related_name="homecell", 
        blank=True, 
        null=True
    )
    category = models.CharField(
        max_length=24, 
        blank=True, 
        choices=AttendanceCategories.choices,
        default=AttendanceCategories.SUNDAY
    )
    preacher = models.CharField(max_length=255, blank=True)
    sermon = models.TextField(blank=True)
    scriptures = models.TextField(blank=True)
    headcount = models.BigIntegerField(default=0)
    adults = models.BigIntegerField(default=0)
    children = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    newcomers = models.BigIntegerField(default=0)
    altar_call = models.BigIntegerField(default=0)
    baptism = models.BigIntegerField(default=0)
    summary = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, blank=True)
    start_time = models.DateTimeField(
        null=True, 
        blank=True, 
        default=timezone.make_aware(datetime(1900, 1, 1, 0, 0, 0))
    )
    end_time = models.DateTimeField(
        null=True, 
        blank=True, 
        default=timezone.make_aware(datetime(1900, 1, 1, 0, 0, 0))
    )
    timestamp = models.DateField(
        null=True, 
        blank=True, 
        default=date(1900, 1, 1),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "attendance"
        verbose_name_plural = "attendance"
        ordering = ["-timestamp"] 

    def __str__(self):
        return f"{self.timestamp} - {self.church} - {self.category}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.church.name, allow_unicode=True)
            sermon_slug = slugify(self.sermon, allow_unicode=True)
            self.slug = f"{sermon_slug}-{base_slug}"
            counter = 1
            while Attendance.objects.filter(slug=self.slug).exists():
                self.slug = f"{sermon_slug}-{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)





class HCAttendance(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.CASCADE, related_name="hc_church"
    )
    homecell = models.ForeignKey(
        Homecell, on_delete=models.CASCADE, related_name="homecell_attend", null=True
    )
    editor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="homecell_editor", 
        blank=True, 
        null=True
    )
    coordinator = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    venue = models.CharField(max_length=255)
    total_attendance = models.BigIntegerField(default=0)
    adults = models.BigIntegerField(default=0)
    kids = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    new_members = models.BigIntegerField(default=0)
    altar_call = models.BigIntegerField(default=0)
    scriptures = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Homecell Attendance"
        verbose_name_plural = "Homecell Attendance"
        ordering = ["start_time"]

    def save(self, *args, **kwargs):
        if not self.slug:
            name_slug = slugify(self.homecell.group_name)  # type: ignore
            base_slug = slugify(self.topic)  # type: ignore
            self.slug = f"{name_slug}-{base_slug}"
            counter = 1
            while HCAttendance.objects.filter(slug=self.slug).exists():
                self.slug = f"{name_slug}-{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.homecell}"


# class Testimony(models.Model):
#     attendance = models.ForeignKey(
#         Attendance, 
#         on_delete=models.CASCADE, 
#         related_name="testimonies"
#     )
#     member = models.CharField(max_length=255, blank=True)
#     description = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = "testimony"
#         verbose_name_plural = "testimonies"
#         ordering = ["-created_at"]

#     def __str__(self):
#         return f"{self.attendance.church.name} {self.member}"  # type: ignore











