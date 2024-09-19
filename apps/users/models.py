import uuid
import random
from PIL import Image
from decimal import Decimal
from django.db import models
from datetime import date, datetime
from apps.users.choices import UserRoles
from apps.users.utils import user_avatar_url
from django.db.models.expressions import Value
from imagekit.models import ProcessedImageField
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from imagekit.processors import ResizeToFill, SmartResize
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin

class UserRoles(models.TextChoices):
    PRESIDENT = 'President', 'President'
    SENIOR_PASTOR = 'Senior Pastor', 'Senior Pastor'
    OVERSEER = 'Overseer', 'Overseer'
    MODERATOR = 'Moderator', 'Moderator'
    PASTOR = 'Pastor', 'Pastor'
    SECRETARY = 'Secretary', 'Secretary'
    SECRETARY_GENERAL = 'Secretary General', 'Secretary General'
    ADMIN = 'Admin', 'Admin'
    DELEGATE = 'Delegate', 'Delegate'

class CustomUserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, username=None, password=None, role=None, church=None):
        if not first_name:
            raise ValueError('Users must have a first name')
        if not last_name:
            raise ValueError('Users must have a last name')
        if not email:
            raise ValueError('Users must have an email address')

        if username is None:
            username = str(uuid.uuid4())

        if role is None:
            role = 'Secretary'
    
        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            username=username,
            role=role,
            church=church,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, first_name, last_name, email, username=None, password=None, role=None):
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            role=role,
            password=password,
        )
        user.is_admin=True
        user.is_superuser=True
        user.save(using=self._db)
        return user
    
   
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.UUIDField(
        default=uuid.uuid4, 
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
    church = models.ForeignKey(
        related_name='church', 
        on_delete=models.CASCADE,
        to="churches.Church",
        null=True,
        blank=True
    )
    churches = models.ManyToManyField(
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
        max_length=12,
        blank=True,
    )
    role = models.CharField(
        max_length=24,
        blank=True,
        choices=UserRoles.choices,
        default=UserRoles.SECRETARY
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role', 'church']

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

    @property
    def is_staff(self):
        return self.is_admin


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


class Account(models.Model):
    ACCOUNT_CHOICES = (
        ('Free', 'Free'),
        ('Premium', 'Premium'),
    )
    
    ACCOUNT_PAYMENT_METHODS = (
        ('Cash', 'Cash'),
        ('Visa', 'Visa'),
        ('Mastercard', 'Mastercard'),
    )
    
    ACCOUNT_INTERVALS_CHOICES = (
        (1, 'Monthly'),
        (4, 'Quarterly'),
        (12, 'Annually')
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='account',
    )
    type = models.CharField(
        max_length=255, 
        blank=True,
        choices=ACCOUNT_CHOICES,
        default='Free'
    )
    method = models.CharField(
        max_length=255, 
        blank=True,
        choices=ACCOUNT_PAYMENT_METHODS
    )
    intervals = models.IntegerField(
        default=0,
        choices=ACCOUNT_INTERVALS_CHOICES
    )
    premium_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal(5),
    )
    sub_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal(0.00),
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal(0.00),
    )
    amount_due = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal(0.00),
    )
    amount_paid = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal(0.00)
    )
    expires = models.DateTimeField(
        blank=True,
        null=True
    )
    created = models.DateTimeField(auto_now_add=True, null=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'account'
        verbose_name_plural = 'accounts'
        ordering = ['-created']
    
    
    def __str__(self):
        return self.user.username # type: ignore
    
    
    def save(self, *args, **kwargs):
        if(self.intervals == 4):
            self.sub_total = self.premium_fee * self.intervals
            self.discount = self.sub_total * 8 / 100
            self.amount_due = ((self.sub_total - self.discount) - self.amount_paid)
        elif(self.intervals == 12):
            self.sub_total = self.premium_fee * self.intervals
            self.discount = self.sub_total * 15 / 100
            self.amount_due = ((self.sub_total - self.discount) - self.amount_paid)
        else:
            self.sub_total = self.premium_fee * self.intervals
            self.discount = self.sub_total * 0 / 100
            self.amount_due = ((self.sub_total - self.discount) - self.amount_paid)
        super().save(*args, **kwargs)
    
    
    @property
    def is_premium_active(self):
        TOTAL_FEE = self.sub_total - self.discount
        return self.type == 'Premium' and self.amount_due == 0.00 and self.amount_paid != 0.00 and self.amount_paid == TOTAL_FEE




