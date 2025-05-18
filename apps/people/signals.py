import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.people.models import Member, JuniorMember
from apps.shared.utils import generate_oklch_color

@receiver(post_save, sender=Member)
def save_member(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        # generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.avatar_fallback = generate_oklch_color()
        instance.save()
        
        
@receiver(post_save, sender=JuniorMember)
def save_kindred(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.avatar_fallback = generated_hex_code
        instance.save()