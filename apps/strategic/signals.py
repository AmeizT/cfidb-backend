import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.strategic.models import StrategyLegacy, Strategy

def generate_hex():
    return random.randint(0, 255)

@receiver(post_save, sender=StrategyLegacy)
def save_member_legacy(sender, instance, created, **kwargs):
    if created:
        instance.color = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
        instance.save()

@receiver(post_save, sender=Strategy)
def save_member(sender, instance, created, **kwargs):
    if created:
        instance.banner_fallback = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
        instance.save()

        
        