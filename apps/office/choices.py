from django.db import models

class StatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    DISAPPROVED = 'disapproved', 'Disapproved'


class DocumentCategoryChoices(models.TextChoices):
    STRATEGY = 'strategy', 'Strategy'
    PRESIDENT = 'president', 'President Circular'
    GENERAL_OVERSEER = 'general', 'General Overseer Circular'
    NATIONAL_OVERSEER = 'national', 'National Overseer Circular'
    SECRETARY_GENERAL = 'secretary', 'Secretary General Circular'


class MeetingCategoryChoices(models.TextChoices):
    BOARD = 'board', 'Board'
    DEACONS = 'deacons', 'Deacons'
    ELDERS = 'elders', 'Elders'
    PASTORS = 'pastors', 'Pastors'
    WORKERS = 'workers', 'Workers'
    YOUTH = 'youth', 'Youth'