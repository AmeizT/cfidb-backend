import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.users.models import User, Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
        
        Profile.objects.create(user=instance)
        
        instance.avatar_fallback = generated_hex_code
        instance.save()
