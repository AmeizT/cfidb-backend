from django.dispatch import receiver
from django.db.models.signals import pre_save
from apps.core.models import TermsAndConditions

@receiver(pre_save, sender=TermsAndConditions)
def update_version(sender, instance, **kwargs):
    if instance.pk:
        last_version = sender.objects.order_by('-created_at').first()
        if last_version:
            major, minor = map(int, last_version.version.split('.'))
            minor += 1
            instance.version = f"{major}.{minor}"