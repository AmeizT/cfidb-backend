from django.db import models

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




