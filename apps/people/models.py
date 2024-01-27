import uuid
from enum import Enum
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.users.models import User
from datetime import date, datetime
from django.utils.text import slugify
from apps.churches.models import Church
from django.forms import ValidationError
from django.core.validators import RegexValidator
from apps.people.choices import (
    AttendanceCategories,
    ChurchRoles, 
    Gender, 
    GuardianRelationship,
    MembershipStatus,
    Ministries, 
    Prefixes, 
    Relationship,
)


class Member(models.Model):
    member_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name="members"
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="editor", 
        blank=True, 
        null=True
    )
    prefix = models.CharField(
        max_length=255, 
        choices=Prefixes.choices, 
        blank=True
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
    relationship = models.CharField(
        max_length=255, 
        blank=True, 
        choices=Relationship.choices
    )
    occupation = models.CharField(
        max_length=255, 
        blank=True
    )
    address = models.TextField(
        blank=True
    )
    city = models.CharField(
        max_length=255, 
        blank=True
    )
    country = models.CharField(max_length=255)
    phone_number = models.CharField(
        max_length=24, 
        blank=True
    )
    email = models.EmailField(blank=True)
    membersince = models.DateField()
    membership_status = models.CharField(
        max_length=255, 
        blank=True,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ESTABLISHED
    )
    ministry = models.CharField(
        max_length=255, 
        blank=True, 
        choices=Ministries.choices
    )
    position = models.CharField(
        max_length=255, 
        blank=True, 
        choices=ChurchRoles.choices
    )
    baptized_at = models.DateField(
        blank=True,
        null=True,
        default=date(1900, 1, 1),
    )
    tithes = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00)
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar_fallback = models.CharField(
        max_length=24, 
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Member"
        verbose_name_plural = "Members"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            if Member.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth,
                phone_number=self.phone_number,
            ).exists():
                raise ValidationError(
                    "A member with the same name, date of birth, and phone number already exists."
                )
        super(Member, self).save(*args, **kwargs)
        
                
class Kindred(models.Model):
    member_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
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
        verbose_name = "kindred"
        verbose_name_plural = "kindred"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            if Kindred.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth,
            ).exists():
                raise ValidationError(
                    "A member with the same name, date of birth, and phone_number number already exists."
                )
        super(Kindred, self).save(*args, **kwargs)
        
 
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
        ordering = ["-timestamp"]
        verbose_name = "tally"
        verbose_name_plural = "tallies"
        

    def __str__(self):
        return f"{self.branch.name}"
 
                         
class Homecell(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.CASCADE, related_name="homecell"
    )
    group_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(Member, blank=True)
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
        ordering = ["group_name"]

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
        related_name="homecell_attendance", 
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
    attendance_count = models.BigIntegerField(default=0)
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
    attendance_date = models.DateField(
        null=True, 
        blank=True, 
        default=date(1900, 1, 1),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "attendance"
        verbose_name_plural = "attendance"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.church}"
    
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











