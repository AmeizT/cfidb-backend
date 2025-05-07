from django.db import models

class UserRoles(models.TextChoices):
    ADMIN = 'Admin', 'Admin'
    DELEGATE = 'Delegate', 'Delegate'
    DEAN = 'Dean', 'Dean'
    MODERATOR = 'Moderator', 'Moderator'
    OVERSEER = 'Overseer', 'Overseer'
    PASTOR = 'Pastor', 'Pastor'
    PRESIDENT = 'President', 'President'
    SECRETARY = 'Secretary', 'Secretary'
    SECRETARY_GENERAL = 'Secretary General', 'Secretary General'
    SENIOR_PASTOR = 'Senior Pastor', 'Senior Pastor'
    STUDENT = 'Student', 'Student'
    STUDENT_REPRESENTATIVE = 'Student Representative', 'Student Representative'
    TEACHER = 'TEACHER', 'TEACHER'




