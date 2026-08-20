import uuid
from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.churches.utils import church_images_path, generate_oklch_color, generate_zone_code
from django.utils.translation import gettext_lazy as _

from apps.churches.utils.generate_assembly_code import generate_assembly_code
from nanoid import generate

def generate_public_id():
    return generate(size=21)

class ChurchStatus(models.TextChoices):
    CLOSED = "closed", _("Closed")
    OPEN = "open", _("Open")
    MERGED = "merged", _("Merged")
    SUSPENDED = "suspended", _("Suspended")

class Church(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    public_id = models.CharField(
        max_length=21,
        default=generate_public_id,
        editable=True,
        db_index=True,
    )
    code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Short assembly code, e.g. CFI-EAZ-026"),
    )
    assigned_pastors = models.ManyToManyField(
        User,
        related_name='pastor_of',
        blank=True, 
    )
    name = models.CharField(
        max_length=100, 
        unique=True
    )
    zone = models.ForeignKey(
        "churches.Zone",
        related_name='assemblies',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=3, blank=True)
    locale = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Locale used for formatting, e.g. en-ZW, en-ZA, en-NA"),
    )
    currency = models.CharField(max_length=12, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10,
        blank=True,
        choices=ChurchStatus.choices, 
        default=ChurchStatus.OPEN, 
    )
    avatar = models.ImageField(
        upload_to=church_images_path, 
        blank=True
    )
    avatar_fallback = models.CharField(
        max_length=36, 
        blank=True
    )
    cover_image = models.ImageField(
        upload_to=church_images_path,
        blank=True
    )
    cover_image_position = models.CharField(
        max_length=20,
        default="center"
    )
    established_date = models.DateField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Assembly"
        verbose_name_plural = "Assemblies"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country_code"]),
            models.Index(fields=["zone"]),
            models.Index(fields=["status"]),
        ]
        
    def __str__(self):
        return self.name
    
    @property
    def primary_currency(self):
        return self.currencies.filter(is_primary=True, is_active=True).first() # type: ignore

    @property
    def member_count(self):
        return self.members.count() # type: ignore
    
    @property
    def total_members(self):
        members_count = self.members.count()  # type: ignore
        minors_count = self.kindred.count()    # type: ignore
        return members_count + minors_count
    
    @property
    def years_active(self):
        if not self.established_date:
            return None

        today = timezone.localdate()
        years = today.year - self.established_date.year

        if (today.month, today.day) < (
            self.established_date.month,
            self.established_date.day,
        ):
            years -= 1

        return years
    

    def save(self, *args, **kwargs):
        if not self.avatar_fallback:
            self.avatar_fallback = generate_oklch_color()

        if not self.code and self.name:
            base_code = generate_assembly_code(self.name)
            code = base_code
            counter = 2

            while Church.objects.filter(code=code).exclude(pk=self.pk).exists():
                code = f"{base_code}-{counter:03d}"
                counter += 1

            self.code = code

        if self.country_code:
            self.country_code = self.country_code.upper()

        if self.locale:
            self.locale = self.locale.strip()

        super().save(*args, **kwargs)



class AssemblyCurrency(models.Model):
    assembly = models.ForeignKey(
        Church,
        related_name="currencies",
        on_delete=models.CASCADE,
    )

    currency = models.CharField(
        max_length=3,
        help_text=_("ISO currency code, e.g. USD, ZAR, NAD, ZWG"),
    )

    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assembly Currency"
        verbose_name_plural = "Assembly Currencies"
        ordering = ["-is_primary", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["assembly", "currency"],
                name="unique_currency_per_assembly",
            ),
            models.UniqueConstraint(
                fields=["assembly"],
                condition=models.Q(is_primary=True),
                name="unique_primary_currency_per_assembly",
            ),
        ]

    def __str__(self):
        label = "Primary" if self.is_primary else "Secondary"
        return f"{self.assembly.name} - {self.currency} ({label})"

    def save(self, *args, **kwargs):
        if self.currency:
            self.currency = self.currency.upper()

        super().save(*args, **kwargs)