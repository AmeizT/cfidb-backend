import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.office.models import Circular, Meeting

@receiver(post_save, sender=Circular)
def save_member(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.color_id = generated_hex_code
        instance.save()


@receiver(post_save, sender=Meeting)
def save_member(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
         
        instance.color_id = generated_hex_code
        instance.save()
        
    