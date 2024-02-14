from django.db import models

class StrategyStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    DISAPPROVED = 'disapproved', 'Disapproved'


class DocumentCategoryChoices(models.TextChoices):
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


class MeetingAttendanceChoices(models.TextChoices):
    PERSON = 'in-person', 'In Person'
    VIRTUAL = 'virtual', 'Virtual'
    

class MeetingPlatformChoices(models.TextChoices):
    FACEBOOK = 'facebook', 'Facebook'
    MEET = 'meet', 'Google Meet'
    SLACK = 'slack', 'Slack'
    TEAMS = 'teams', 'Microsoft Teams'
    TELEGRAM = 'telegram', 'Telegram'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    ZOOM = 'zoom', 'Zoom'