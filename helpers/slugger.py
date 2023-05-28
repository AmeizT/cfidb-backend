from django.utils.text import slugify
from apps.events.models import Event

def unqie_event_slug(self):
    if not self.slug:
        base_slug = slugify(self.title)
        self.slug = base_slug
        counter = 1
        while Event.objects.filter(slug=self.slug).exists():
            self.slug = f"{base_slug}-{counter}"
            counter += 1