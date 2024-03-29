# Generated by Django 5.0.1 on 2024-01-14 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('office', '0005_document_delete_circular'),
    ]

    operations = [
        migrations.RenameField(
            model_name='document',
            old_name='thumbnail_fallback',
            new_name='document_thumbnail_fallback',
        ),
        migrations.RenameField(
            model_name='meeting',
            old_name='color_id',
            new_name='meeting_thumbnail_fallback',
        ),
        migrations.AlterField(
            model_name='document',
            name='category',
            field=models.CharField(blank=True, choices=[('strategy', 'Strategy'), ('president', 'President Circular'), ('general overseer circular', 'General Overseer Circular'), ('national overseer circular', 'National Overseer Circular'), ('secretary general circular', 'Secretary General Circular')], max_length=255),
        ),
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(blank=True, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('disapproved', 'Disapproved')], default='pending', max_length=255),
        ),
    ]
