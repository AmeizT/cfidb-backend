import random
from django.dispatch import receiver
from apps.office.models import Meeting
from django.db.models.signals import post_save
from utils.random_color import generate_random_color 
from apps.office.abstract import AbstractBaseDocument

@receiver(post_save, sender=Meeting)
def save_meeting_thumbnail_fallback(sender, instance, created, **kwargs):
    if created:         
        instance.meeting_thumbnail_fallback = generate_random_color() 
        instance.save()

@receiver(post_save, sender=AbstractBaseDocument)
def save_document_thumbnail_fallback(sender, instance, created, **kwargs):
    if created:         
        instance.document_thumbnail_fallback = generate_random_color() 
        instance.save()



        
    