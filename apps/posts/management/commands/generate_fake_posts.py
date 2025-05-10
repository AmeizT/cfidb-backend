from django.core.management.base import BaseCommand
from apps.posts.models import Post, PostImage
from apps.users.models import User
from apps.churches.models import Church
from django.utils.text import slugify
from faker import Faker # type: ignore
import random
import requests
from django.core.files.base import ContentFile
from io import BytesIO

fake = Faker()

class Command(BaseCommand):
    help = "Generate 20 fake posts with random Unsplash images"

    def handle(self, *args, **kwargs):
        authors = User.objects.all()
        churches = Church.objects.all()

        if not authors.exists() or not churches.exists():
            self.stdout.write(self.style.ERROR("You need users and churches to create posts."))
            return

        for _ in range(20):
            author = random.choice(authors)
            assembly = random.choice(churches)
            title = fake.sentence()
            content = fake.paragraph(nb_sentences=5)

            post = Post.objects.create(
                author=author,
                assembly=assembly,
                title=title,
                content=content,
            )

            # Add 1-3 random Unsplash images
            for _ in range(random.randint(1, 3)):
                response = requests.get("https://source.unsplash.com/random/800x600", stream=True)
                if response.status_code == 200:
                    img_name = f"unsplash_{random.randint(1000,9999)}.jpg"
                    image_file = ContentFile(response.content)
                    image_file.name = img_name
                    post_image = PostImage(
                        post=post,
                        alt=fake.sentence(),
                        caption=fake.sentence()
                    )
                    post_image.image.save(img_name, image_file, save=True)

        self.stdout.write(self.style.SUCCESS("Successfully created 20 fake posts with images"))