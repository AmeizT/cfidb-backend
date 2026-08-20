from django.db import models

class ServiceType(models.TextChoices):
    MAIN = "MAIN", "Main Service"
    BIBLE_STUDY = "BIBLE_STUDY", "Bible Study"
    PRAYER = "PRAYER", "Prayer"

class AttendanceCategories(models.TextChoices):
    FRIDAY = 'friday', 'Friday'
    HOMECELL = 'homecell', 'Homecell'
    OUTREACH = 'outreach', 'Outreach'
    OTHER = 'other', 'Other'
    SUNDAY = 'sunday', 'Sunday'


class SundaySchoolClassChoices(models.TextChoices):
    BEGINNERS = "beginners", "Beginners"
    PRIMARY = "primary", "Primary"
    JUNIORS = "juniors", "Juniors"
    INTERMEDIATE = "intermediate", "Intermediate"
    TEENS = "teens", "Teens"
