import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.people.models import Member

@receiver(post_save, sender=Member)
def save_account(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.avatar_fallback_color = generated_hex_code
        instance.save()