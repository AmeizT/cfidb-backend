import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.churches.models import Church

@receiver(post_save, sender=Church)
def save_account(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.brand = generated_hex_code
        instance.save()