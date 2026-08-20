from django.db import models
from apps.churches.models import Church
from apps.bookkeeper.models.base import FinancialBase
from apps.reports.mixins.audit import AuditLogMixin
from django.core.exceptions import ValidationError

class OverheadType(models.Model):
    name = models.CharField(max_length=100)
    is_global = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    assembly = models.ForeignKey(
        Church,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="overhead_types"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "name"],
                name="unique_overhead_type_per_assembly"
            )
        ]

    def clean(self):
        if self.is_global and self.assembly:
            raise ValidationError("Global types cannot belong to an assembly.")

        if not self.is_global and not self.assembly:
            raise ValidationError("Assembly-specific types must belong to an assembly.")

    def __str__(self):
        return self.name
    

class Overhead(AuditLogMixin, FinancialBase):
    AUDIT_TRANSACTION_TYPE = "Overhead"

    overhead_type = models.ForeignKey(
        OverheadType,
        on_delete=models.PROTECT,
        related_name="overheads"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "overhead_type"],
                name="unique_report_overhead_type"
            )
        ]
        indexes = [
            models.Index(fields=["assembly"]),
            models.Index(fields=["report"]),
        ]

    # ----------------------------
    # Validation
    # ----------------------------
    def clean(self):
        if self.report and self.assembly:
            if self.report.assembly != self.assembly:
                raise ValidationError("Assembly must match the report's assembly.")

    # ----------------------------
    # Save Logic
    # ----------------------------
    def save(self, *args, **kwargs):
        # Auto-assign report if missing
        self.assign_report()

        # Ensure transaction falls within valid reporting period
        self.validate_period()

        # Run model validation
        self.full_clean()

        super().save(*args, **kwargs)

        # Update report totals after save
        self.update_report_totals()

    # ----------------------------
    # Audit Snapshot
    # ----------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.pk:
            self._old_data = {
                "amount": str(self.amount),
                "notes": self.notes,
                "overhead_type": (
                    self.overhead_type.name
                    if self.overhead_type_id else None
                ),
            }
        else:
            self._old_data = None

    # ----------------------------
    # String Representation
    # ----------------------------
    def __str__(self):
        return f"{self.assembly.name} - {self.overhead_type.name} - {self.amount}"
    


from django.db import models
from apps.churches.models import Church
from apps.bookkeeper.models import FinancialBase
from apps.bookkeeper.utils import bank_statement_path
from apps.reports.mixins.audit import AuditLogMixin
from django.core.exceptions import ValidationError

class RevenueCategory(models.Model):
    assembly = models.ForeignKey(Church, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    is_standard = models.BooleanField(default=False)  
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("assembly", "name")

    def __str__(self):
        return f"{self.name} ({'Standard' if self.is_standard else 'Custom'})"
    

class Revenue(AuditLogMixin, FinancialBase):
    """
    Revenue linked to a category. Categories can be standard or user-created.
    """

    AUDIT_TRANSACTION_TYPE = "Revenue"

    category = models.ForeignKey(
        RevenueCategory,
        on_delete=models.PROTECT,
        related_name="revenues"
    )

    statement = models.FileField(
        upload_to=bank_statement_path,
        blank=True,
        null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "category"],
                name="unique_report_category"
            )
        ]
        indexes = [
            models.Index(fields=["assembly"]),
            models.Index(fields=["report"]),
        ]

    # ----------------------------
    # Validation
    # ----------------------------
    def clean(self):
        if self.report and self.assembly:
            if self.report.assembly != self.assembly:
                raise ValidationError("Assembly must match the report's assembly.")

    # ----------------------------
    # Save Logic
    # ----------------------------
    def save(self, *args, **kwargs):
        self.assign_report()
        self.validate_period()
        self.full_clean()  # <-- critical
        super().save(*args, **kwargs)
        self.update_report_totals()

    # ----------------------------
    # Audit Snapshot
    # ----------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.pk:
            self._old_data = {
                "amount": str(self.amount),
                "notes": self.notes,
                "category": (
                    self.category.name
                    if self.category_id else None
                ),
            }
        else:
            self._old_data = None

    # ----------------------------
    # String Representation
    # ----------------------------
    def __str__(self):
        return f"{self.assembly.name} - {self.category.name} - {self.amount}"



from decimal import Decimal
from django.db import models
from apps.users.models import User
from apps.churches.models import Church
from apps.bookkeeper.utils import (
    asset_image_path,
    asset_images_path
)
from django.db.models import Sum
from imagekit.models import ProcessedImageField
from imagekit.processors import SmartResize

class AssetType(models.TextChoices):
    BUILDING = 'Building', 'Building'
    INSTRUMENT = 'Instrument', 'Instrument'
    VEHICLE = 'Vehicle', 'Vehicle'
    FURNITURE = 'Furniture', 'Furniture'
    ELECTRONICS = 'Electronics', 'Electronics'
    MACHINERY = 'Machinery', 'Machinery'
    SOFTWARE = 'Software', 'Software'
    LAND = 'Land', 'Land'
    OTHER = 'Other', 'Other'


class Condition(models.TextChoices):
    NEW = 'New', 'New'
    GOOD = 'Good', 'Good'
    FAIR = 'Fair', 'Fair'
    OLD = 'Old', 'Old'
    NOT_WORKING = 'Not Working', 'Not Working'



class Asset(models.Model):
    assembly = models.ForeignKey(
        Church, 
        related_name='assets',
        on_delete=models.CASCADE
    )
    item_code = models.CharField(max_length=255, blank=True)
    item_name = models.CharField(max_length=255)
    acquisition_date = models.DateField()
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices
    )
    description = models.TextField(max_length=2000, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    units = models.PositiveIntegerField()
    acquisition_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    residual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    status = models.CharField(
        max_length=255,
        blank=True
    )
    image = ProcessedImageField(
        upload_to=asset_image_path,
        processors=[SmartResize(width=1080, height=1350)],
        format='WEBP',
        options={'quality': 70},
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="assets_editor",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
        ordering = ['item_name']

    def __str__(self):
        return f"{self.assembly.name} - {self.item_name}"

class AssetImage(models.Model):
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='asset_images'
    )
    image = ProcessedImageField(
        upload_to=asset_images_path,
        # processors=[SmartResize(width=1080, height=1350)],
        format='WEBP', # type: ignore
        options={'quality': 80} # type: ignore
    )
    
    class Meta:
        verbose_name = 'Asset Image'
        verbose_name_plural = 'Asset Images'
        
        
    def __str__(self):
        return self.asset.item_name


from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.people.models import Member
from apps.bookkeeper.models import FinancialBase
from apps.bookkeeper.utils import tithe_receipt_path
from apps.reports.mixins.audit import AuditLogMixin


class PaymentMethod(models.TextChoices):
    BANK = 'Bank', 'Bank'
    CASH = 'Cash', 'Cash'
    CHEQUE = 'Cheque', 'Cheque'
    PBP = 'Payment By Phone', 'Payment By Phone'
    OTHER = 'Other', 'Other'


class TitheManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_trash=False)

    def trashed(self):
        return super().get_queryset().filter(is_trash=True)


class Tithe(AuditLogMixin, FinancialBase):
    member = models.ForeignKey(
        "people.Member",
        on_delete=models.PROTECT,
        related_name='tithes',
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    payment_method = models.CharField(
        max_length=26,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK,
    )

    receipt = models.FileField(
        upload_to=tithe_receipt_path,
        null=True,
        blank=True,
    )
    reference_code = models.CharField(max_length=100, blank=True)
    is_trash = models.BooleanField(default=False)
    trash_date = models.DateTimeField(null=True, blank=True)

    objects = TitheManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Tithe"
        verbose_name_plural = "Tithes"
        ordering = ["-timestamp"]

    def __str__(self):
        member_name = self.member.full_name if self.member else "Anonymous"
        return f"{member_name}, {self.timestamp} - {self.assembly.name}"

    # --- Soft delete ---
    def delete(self, using=None, keep_parents=False):
        self.is_trash = True
        self.trash_date = timezone.now()
        self.save()

    def restore(self):
        self.is_trash = False
        self.trash_date = None
        self.save()

    def save(self, *args, **kwargs):
        self.assign_report()
        super().save(*args, **kwargs)


from django.db import models
from apps.churches.models import Church

class MonthlyFinanceSnapshot(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name="finance_snapshots")
    year = models.IntegerField()
    month = models.IntegerField()
    gross_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tithes = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    book_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.church.name} - {self.month}/{self.year}"


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
from imagekit.processors import SmartResize
from imagekit.models import ProcessedImageField
from apps.people.choices import (
    EducationLevel,
    Gender, 
    GuardianRelationship,
    MembershipStatus,
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
        return (
            not self.is_trash and
            self.membership_status not in ['Deceased', 'Inactive']
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


from django.db import models
from apps.reports.models import AuditLog
from apps.reports.mixins import AuditLogMixin
from apps.reports.models import AssemblyReport
from apps.people.choices.weather import WeatherCondition
from apps.people.choices.services import AttendanceCategories


class Attendance(AuditLogMixin, models.Model):
    AUDIT_TRANSACTION_TYPE = "Attendance"

    assembly = models.ForeignKey(
        "churches.Church",
        on_delete=models.CASCADE,
        related_name="attendances",
        db_index=True
    )

    report = models.ForeignKey(
        AssemblyReport,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendances"
    )

    homecell = models.ForeignKey(
        "people.Homecell",
        on_delete=models.SET_NULL,
        related_name="attendances",
        null=True,
        blank=True
    )

    service_type = models.CharField(
        max_length=24,
        choices=AttendanceCategories.choices,
        default=AttendanceCategories.SUNDAY,
        db_index=True
    )

    is_special_event = models.BooleanField(default=False)
    special_event_name = models.CharField(max_length=255, blank=True)
    weather = models.CharField(
        max_length=30,
        choices=WeatherCondition.choices,
        null=True,
        blank=True,
        db_index=True
    )
    preacher = models.CharField(max_length=255, blank=True)
    sermon = models.TextField(blank=True)
    scriptures = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Numeric metrics
    adults = models.PositiveIntegerField(default=0)
    children = models.PositiveIntegerField(default=0)
    guest_attendance = models.PositiveIntegerField(default=0)
    new_converts = models.PositiveIntegerField(default=0)
    altar_call = models.PositiveIntegerField(default=0)
    baptisms = models.PositiveIntegerField(default=0)
    online_viewers = models.PositiveIntegerField(default=0)
    volunteers_on_duty = models.PositiveIntegerField(default=0)
    total_leaders_present = models.PositiveIntegerField(default=0)

    is_deleted = models.BooleanField(default=False)

    timestamp = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    NUMERIC_FIELDS = [
        "adults",
        "children",
        "guest_attendance",
        "new_converts",
        "baptisms",
        "altar_call",
        "online_viewers",
        "volunteers_on_duty",
        "total_leaders_present",
    ]

    class Meta:
        ordering = ["-timestamp"]
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "timestamp", "service_type", "homecell"],
                name="unique_service_attendance"
            )
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.assembly.name} - {self.service_type}"

    @property
    def headcount(self):
        return self.adults + self.children + self.guest_attendance

    def numeric_fields_changed(self):
        if not self.pk:
            return True
        old = Attendance.objects.get(pk=self.pk)
        return any(getattr(old, f) != getattr(self, f) for f in self.NUMERIC_FIELDS)

    def assign_report(self):
        if self.report:
            return

        report = AssemblyReport.objects.filter(
            assembly=self.assembly,
            period_start__lte=self.timestamp,
            period_end__gte=self.timestamp,
            status=AssemblyReport.Status.DRAFT
        ).first()

        if not report:
            import calendar
            period_start = self.timestamp.replace(day=1)
            last_day = calendar.monthrange(self.timestamp.year, self.timestamp.month)[1]
            period_end = self.timestamp.replace(day=last_day)

            report = AssemblyReport.objects.create(
                assembly=self.assembly,
                period_start=period_start,
                period_end=period_end,
                status=AssemblyReport.Status.DRAFT
            )

        self.report = report

    def save(self, *args, **kwargs):
        is_create = not self.pk
        numeric_changed = self.numeric_fields_changed()

        self.assign_report()
        super().save(*args, **kwargs)

        if numeric_changed and self.report:
            self.report.recalculate_attendance_totals()
            zone_report = getattr(self.report, "zone_report", None)
            if zone_report:
                zone_report.recalculate_from_assemblies()

        if hasattr(self, "log_audit"):
            self.log_audit(
                user=getattr(self, "_current_user", None),
                action=AuditLog.Action.CREATE if is_create else AuditLog.Action.UPDATE
            )