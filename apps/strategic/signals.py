import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.strategic.models import StrategyLegacy

@receiver(post_save, sender=StrategyLegacy)
def save_member(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.color = generated_hex_code
        instance.save()
        
        