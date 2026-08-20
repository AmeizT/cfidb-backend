from django.db import models

class MembershipStatus(models.TextChoices):
    VISITOR = 'Visitor', 'Visitor'
    REGULAR = 'Regular', 'Regular Attendee'
    ESTABLISHED = 'Established', 'Established'
    RELOCATED = 'Relocated', 'Relocated (Living Abroad)'
    INACTIVE = 'Inactive', 'Inactive'
    TRANSFERRED = 'Transferred', 'Transferred to Another Church'
    DECEASED = 'Deceased', 'Deceased'