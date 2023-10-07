import uuid
from decimal import Decimal
from django.db import models
from apps.users.models import User
from django.utils.text import slugify
from apps.churches.models import Church
from django.forms import ValidationError
from django.core.validators import RegexValidator
from apps.people.choices import (
    CHURCH_POSITIONS_CHOICES, 
    GENDER_CHOICES, 
    MINISTRY_CHOICES, 
    PREFIX_CHOICES, 
    RELATIONSHIP_CHOICES
)


class Attendance(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.CASCADE, related_name="attendance"
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
        verbose_name = "attendance"
        verbose_name_plural = "attendance"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.church}"


class Homecell(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.CASCADE, related_name="homecell"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "homecell"
        verbose_name_plural = "homecells"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"


class HCAttendance(models.Model):
    church = models.ForeignKey(
        Church, on_delete=models.CASCADE, related_name="hc_church"
    )
    homecell = models.ForeignKey(
        Homecell, on_delete=models.CASCADE, related_name="hc_attendance", null=True
    )
    leader = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    venue = models.CharField(max_length=255)
    attendance = models.BigIntegerField(default=0)
    adults = models.BigIntegerField(default=0)
    kids = models.BigIntegerField(default=0)
    visitors = models.BigIntegerField(default=0)
    new = models.BigIntegerField(default=0)
    repented = models.BigIntegerField(default=0)
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
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            name_slug = slugify(self.homecell.name)  # type: ignore
            base_slug = slugify(self.topic)  # type: ignore
            self.slug = f"{name_slug}-{base_slug}"
            counter = 1
            while HCAttendance.objects.filter(slug=self.slug).exists():
                self.slug = f"{name_slug}-{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.homecell}"


class Testimony(models.Model):
    homecell = models.ForeignKey(
        HCAttendance, on_delete=models.CASCADE, related_name="testimonies"
    )
    member = models.CharField(max_length=255, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "testimony"
        verbose_name_plural = "testimonies"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.homecell.homecell.name} {self.member}"  # type: ignore


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
    editor = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="editor", 
        blank=True, 
        null=True
    )
    prefix = models.CharField(
        max_length=255, 
        choices=PREFIX_CHOICES, 
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
        choices=GENDER_CHOICES
    )
    relationship_status = models.CharField(
        max_length=255, 
        blank=True, 
        choices=RELATIONSHIP_CHOICES
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
    baptized_at = models.DateField(
        blank=True,
        null=True
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

        # Save the member if no duplicate entries found
        super(Member, self).save(*args, **kwargs)
        
        
        
class Kin(models.Model):
    RELATIONSHIP_CHOICES = (
        ("Aunt", "Aunt"),
        ("Brother", "Brother"),
        ("Child", "Child"),
        ("Cousin", "Cousin"),
        ("Father", "Father"),
        ("Grandparent", "Grandparent"),
        ("Mother", "Mother"),
        ("Sister", "Sister"),
        ("Spouse", "Spouse"),
        ("Uncle", "Uncle"),
    )

    member_id = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    avatar_fallback_color = models.CharField(
        max_length=24, 
        blank=True
    )
    church = models.ForeignKey(
        Church, 
        on_delete=models.CASCADE, 
        related_name="kin"
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
        choices=GENDER_CHOICES
    )
    guardian = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="guardian"
    )
    relation_with_guardian = models.CharField(
        max_length=255, 
        blank=True, 
        choices=RELATIONSHIP_CHOICES
    )
    membersince = models.DateField()
    date_of_baptism = models.DateField(
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE, 
        related_name="kin_creator",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "kin"
        verbose_name_plural = "kins"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            if Kin.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth,
            ).exists():
                raise ValidationError(
                    "A member with the same name, date of birth, and phone number already exists."
                )

        # Save the member if no duplicate entries found
        super(Kin, self).save(*args, **kwargs)





