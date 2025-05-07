from django.db import models

class PlatformChoices(models.TextChoices):
    DATABASE = "database", "Database"
    ACADEMY = "academy", "Academy"