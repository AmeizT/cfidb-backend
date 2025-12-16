import uuid
import random
from PIL import Image
from decimal import Decimal
from django.db import models
from datetime import date, datetime
from apps.users.choices import UserRoles
from imagekit.processors import SmartResize
from django.db.models.expressions import Value
from imagekit.models import ProcessedImageField
from django.core.validators import RegexValidator
from apps.users.managers import UserManager
from apps.users.utils.nanoid import generate_nanoid
from apps.users.utils.base_urls import user_avatar_url
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

class Role(models.Model):
    name = models.CharField(max_length=50, choices=UserRoles.choices, unique=True)

    class Meta:
        verbose_name = 'role'
        verbose_name_plural = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.CharField(
        max_length=32,
        default=generate_nanoid, 
        editable=False, 
        unique=True
    )
    first_name = models.CharField(
        max_length=255,
        verbose_name='First Name',
    )
    last_name = models.CharField(
        max_length=255,
        verbose_name='Last Name',
    )
    username = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Username',
        blank=True,
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name='Email',
    )
    recovery_email = models.EmailField(
        blank=True,
        null=True,
        unique=True,
        help_text="Used for account recovery or alternative communication."
    )
    church = models.ForeignKey(
        related_name='church', 
        on_delete=models.CASCADE,
        to="churches.Church",
        null=True,
        blank=True
    )
    assemblies = models.ManyToManyField(
        "churches.Church",
        related_name='branches', 
        blank=True
    )
    avatar = ProcessedImageField(
        upload_to=user_avatar_url,
        processors=[SmartResize(width=800, height=800)],
        format='WEBP', 
        options={'quality': 80},
        blank=True,
        null=True,
    )
    avatar_fallback = models.CharField(
        max_length=26,
        blank=True,
    )
    roles = models.ManyToManyField(Role, related_name='users', blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'church']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']
                
    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True
    
    def save(self, *args, **kwargs):
        if not self.username and self.email:
            base_username = self.email.split('@')[0]
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exclude(pk=self.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1

            self.username = username

        super().save(*args, **kwargs)

    DB_STAFF_ROLES = {
        'President',
        'Secretary General',
        'Senior Pastor',
        'Overseer',
        'Moderator',
    }

    DB_ZONE_STAFF_ROLES = {
        'Zone Admin'
    }

    ACADEMY_STAFF_ROLES = {
        'Dean',
        'Teacher',
    }

    ACADEMY_STUDENT_ROLES = {
        'Student',
    }
    
    @property
    def is_student(self):
        return self.roles.filter(name__in=self.ACADEMY_STUDENT_ROLES).exists()

    @property
    def is_db_staff(self):
        return self.roles.filter(name__in=self.DB_STAFF_ROLES).exists()
    
    @property
    def is_db_zone_staff(self):
        return self.roles.filter(name__in=self.DB_ZONE_STAFF_ROLES).exists()

    @property
    def is_academy_staff(self):
        return self.roles.filter(name__in=self.ACADEMY_STAFF_ROLES).exists()

    @property
    def is_staff(self):
        return self.is_db_staff or self.is_academy_staff or self.is_admin
    
    @property
    def full_name(self):
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts).strip()


class Profile(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
    )
    avatar = ProcessedImageField(
        upload_to=user_avatar_url,
        processors=[SmartResize(width=800, height=800)],
        format='WEBP', 
        options={'quality': 80},
        blank=True,
        null=True,
    )
    avatar_fallback = models.CharField(
        max_length=12,
        blank=True,
    )
    iso_country_code = models.CharField(max_length=2, blank=True)
    state_or_province = models.CharField(max_length=26, blank=True)
    country = models.CharField(max_length=26, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'profile'
        verbose_name_plural = 'profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.first_name} {self.user.last_name}'

class AuthHistory(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="auth_history"
    )
    last_login = models.DateTimeField()
    last_logout = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Auth History'
        verbose_name_plural = 'Auth Histories'
        ordering = ['-created_at']
                
    def __str__(self):
        return f'{self.created_at} - {self.user.first_name} {self.user.last_name}'


class PermissionType(models.TextChoices):
    FINANCE = 'finance', 'Finance'
    ATTENDANCE = 'attendance', 'Attendance'
    

class DelegatePermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    permission_type = models.CharField(max_length=20, choices=PermissionType.choices)

    class Meta:
        unique_together = ('user', 'permission_type')

    def __str__(self):
        return f"{self.user.username} - {self.permission_type}"







