from apps.users.utils.nanoid import generate_nanoid
from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, username=None, password=None, church=None):
        if not first_name:
            raise ValueError('Users must have a first name')
        if not last_name:
            raise ValueError('Users must have a last name')
        if not email:
            raise ValueError('Users must have an email address')

        if username is None:
            username = generate_nanoid

    
        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            username=username,
            church=church,
        )
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, first_name, last_name, email, username=None, password=None):
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            password=password,
        )
        user.is_admin=True
        user.is_superuser=True
        user.save(using=self._db)
        return user