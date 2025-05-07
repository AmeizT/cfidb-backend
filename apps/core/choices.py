from django.db import models

class BlogCategoryChoices(models.TextChoices):
    ATTENDANCE = 'Attendance', 'Attendance'
    AUTHENTICATION = 'Authentication', 'Authentication'
    CHANGELOG = "Changelog", "Changelog"
    DEMOGRAPHICS = 'Demographics', 'Demographics'
    FINANCE = 'Finance', 'Finance'
    GENERAL = 'General', 'General'
    STRATEGY = 'Strategy', 'Strategy'
    TEMPLATES = 'Templates', 'Templates'
    UPDATES = 'Updates', 'Updates'


class BlogStatusChoices(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'