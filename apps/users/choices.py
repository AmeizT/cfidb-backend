from django.db import models

class UserRoles(models.TextChoices):
    ADMIN = 'Admin', 'Admin'
    DEAN = 'Dean', 'Dean'
    MODERATOR = 'Moderator', 'Moderator'
    OVERSEER = 'Overseer', 'Overseer'
    PASTOR = 'Pastor', 'Pastor'
    PRESIDENT = 'President', 'President'
    SECRETARY = 'Secretary', 'Secretary'
    SEC_GEN = 'Secretary General', 'Secretary General'
    SENIOR_PASTOR = 'Senior Pastor', 'Senior Pastor'
    STUDENT = 'Student', 'Student'
    STUDENT_REP = 'Student Representative', 'Student Representative'
    TEACHER = 'Teacher', 'Teacher'
    ZONE_ADMIN = 'Zone Admin', 'Zone Admin'




