import uuid
import random
from PIL import Image
from django.db import models
from apps.users.utils import avatarURL
from django.db.models.expressions import Value
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin


class AccountUserManager(BaseUserManager):
    def create_user(self, name, surname, username, email, church, password=None):
        if not name:
            raise ValueError('Users must have a name')
        if not surname:
            raise ValueError('Users must have a surname')
        if not username:
            raise ValueError('Users must have a username')
        if not email:
            raise ValueError('Users must have an email address')
        if not church and not self.model.is_superuser:
            raise ValueError('Users must belong to at one church')

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            surname=surname,
            username=username,
            church=church
        )

        user.set_password(password)
        user.save(using=self._db)
        return user   

    def create_superuser(self, name, surname, username, email, church=None, password=None):
        user = self.create_user(
            name=name,
            surname=surname,
            email=email,
            username=username,
            church=church,
            password=password,
        )
        user.is_admin=True
        user.is_superuser=True
        user.is_pastor=True
        user.is_secretary=True
        user.save(using=self._db)
        return user
    
   
class User(AbstractBaseUser, PermissionsMixin):
    uid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    name = models.CharField(
        max_length=255,
        verbose_name='name',
    )
    surname = models.CharField(
        max_length=255,
        verbose_name='surname',
    )
    username = models.CharField(
        max_length=36,
        unique=True,
        verbose_name='username',
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name='email',
    )
    church = models.ForeignKey(
        related_name='church', 
        on_delete=models.CASCADE,
        to="church.Church",
        null=True
    )
    avatar = models.ImageField( 
        upload_to=avatarURL, 
        null=True, 
        blank=True
    )
    default_background_color = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_pastor = models.BooleanField(default=False)
    is_secretary = models.BooleanField(default=False)
    
    objects = AccountUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname', 'username']

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']
        
        
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.avatar:
            user_image = Image.open(self.avatar)
            if user_image.height > 400 or user_image.width > 400:
                output_size = (400, 400)
                user_image.thumbnail(output_size)
                user_image.save(self.avatar.path)
        
        
    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin











