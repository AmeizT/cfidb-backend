# Generated by Django 5.0.1 on 2024-01-14 16:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('office', '0006_rename_thumbnail_fallback_document_document_thumbnail_fallback_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='remarks',
            field=models.TextField(blank=True),
        ),
    ]
