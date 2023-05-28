import uuid
import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.users.models import User

@receiver(post_save, sender=User)
def save_account(sender, instance, created, **kwargs):
    if created:
        if instance.username is None:
            instance.username = str(uuid.uuid4())
            instance.save()
        
        def generate_hex(): 
            return random.randint(0, 255)

        # Generate a random background color
        background_color = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())

        # Set the default background color
        instance.default_background_color = background_color
        instance.save()
