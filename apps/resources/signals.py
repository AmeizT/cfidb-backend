import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.resources.models import Resource

def generate_hex():
    return random.randint(0, 255)

@receiver(post_save, sender=Resource)
def create_resource_image_fallback(sender, instance, created, **kwargs):
    if created:
        instance.resource_image_fallback = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
        instance.save()