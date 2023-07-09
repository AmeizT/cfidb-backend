import uuid
import random
from django.dispatch import receiver
from django.db.models.signals import post_save
from apps.users.models import User, Account


# @receiver(post_save, sender=User)
# def save_account(sender, instance, created, **kwargs):
#     if created:
#         Account.objects.create(user=instance)
#         def hex(): return random.randint(0, 255)
#         instance.account.avatar_hex = '#%02X%02X%02X' % (hex(), hex(), hex())
#         instance.account.save()
#         instance.save()

@receiver(post_save, sender=User)
def save_account(sender, instance, created, **kwargs):
    if created:
        def generate_hex(): 
            return random.randint(0, 255)

        generated_hex_code = '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
        
        Account.objects.create(user=instance)
        
        instance.avatar_fallback = generated_hex_code
        instance.save()
