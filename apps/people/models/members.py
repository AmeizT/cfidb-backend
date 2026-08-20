import uuid
from nanoid import generate # type: ignore
from django.db import models # type: ignore
from django.utils import timezone # type: ignore
from apps.people.utils import member_avatar_url
from django.contrib.auth.hashers import make_password, check_password # type: ignore
from apps.users.models import User
from datetime import date
from apps.churches.models import Church
from django.forms import ValidationError # type: ignore
from django.core.validators import RegexValidator # type: ignore
from imagekit.processors import SmartResize
from django.db import models # type: ignore
from imagekit.models import ProcessedImageField
from apps.people.choices import (
    EducationLevel,
    Gender, 
    GuardianRelationship,
    MembershipStatus,
    Prefixes, 
    Relationship,
)
from apps.people.models.assembly_membership import AssemblyMembershipStatus


class MembershipStage(models.TextChoices):
    NEW = "new", "New"
    ESTABLISHED = "established", "Established"
    ASSOCIATE = "associate", "Associate"

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
        on_delete=models.SET_NULL,
        related_name="members",
        null=True,
        blank=True,
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
    membership_stage = models.CharField(
        max_length=20,
        choices=MembershipStage.choices,
        default=MembershipStage.ESTABLISHED,
        help_text="Membership maturity/classification; lifecycle is stored on AssemblyMembership.",
    )
    date_of_death = models.DateField(null=True, blank=True)
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
        processors=[SmartResize(width=800, height=800)], # type: ignore
        format='WEBP',  # type: ignore
        options={'quality': 80}, # type: ignore
        blank=True,
        null=True,
    )
    avatar_fallback = models.CharField(
        max_length=64, 
        blank=True
    )
    notes = models.TextField(blank=True) 
    pin_set = models.BooleanField(default=False)
    access_pin = models.CharField(max_length=128, blank=True)
    is_trash = models.BooleanField(default=False)
    trash_date = models.DateTimeField(null=True, blank=True)
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
    
    @property
    def is_active(self):
        membership = self.current_assembly_membership
        return bool(
            not self.is_trash
            and self.date_of_death is None
            and membership
            and membership.status == AssemblyMembershipStatus.ACTIVE
        )
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.member_key}"
    
    def set_access_pin(self, raw_pin):
        self.access_pin = make_password(raw_pin)
        self.pin_set = True
        self.save()

    def verify_access_pin(self, raw_pin):
        return check_password(raw_pin, self.access_pin)
    
    def clean(self):
        """Validate the model before saving."""
        if not self.pk:
            if Member.objects.filter(
                first_name=self.first_name,
                last_name=self.last_name,
                date_of_birth=self.date_of_birth,
                phone_number=self.phone_number,
                is_trash=False,
            ).exists():
                raise ValidationError("A non-trashed member with the same name, date of birth, and phone number already exists.")

        if self.relationship != Relationship.MARRIED and self.marriage_date:
            raise ValidationError({"marriage_date": "Marriage date cannot be set if member is not married."})

    def save(self, *args, **kwargs):
        # Automatically update baptized field based on baptized_at
        if self.baptized_at and self.baptized_at != date(1900, 1, 1):
            self.baptized = True
        else:
            self.baptized = False

        if self.is_trash and not self.trash_date:
            self.trash_date = timezone.now()
        elif not self.is_trash:
            self.trash_date = None

        if not self.member_key:
            self.member_key = generate()
        super(Member, self).save(*args, **kwargs)


    @property
    def current_assembly_membership(self):
        return (
            self.assembly_memberships # type: ignore
            .filter(
                status__in=[
                    AssemblyMembershipStatus.ACTIVE,
                    AssemblyMembershipStatus.INACTIVE,
                ]
            )
            .select_related("assembly")
            .first()
        )


    @property
    def active_household_membership(self):
        return (
            self.household_memberships # type: ignore
            .filter(left_on__isnull=True)
            .select_related("household")
            .first()
        )


    @property
    def household(self):
        membership = self.active_household_membership
        return membership.household if membership else None


class JuniorMember(models.Model):
    member_key = models.UUIDField(
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
