# Generated by Django 4.2.9 on 2024-08-25 22:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0016_alter_imageupload_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bookkeeper', '0033_rename_image_asset_images_alter_assetimage_asset'),
    ]

    operations = [
        migrations.RenameField(
            model_name='asset',
            old_name='valuation',
            new_name='current_value',
        ),
        migrations.RenameField(
            model_name='asset',
            old_name='images',
            new_name='image',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='category',
        ),
        migrations.AddField(
            model_name='asset',
            name='asset_type',
            field=models.CharField(blank=True, choices=[('BUILDING', 'Building'), ('INSTRUMENT', 'Instrument'), ('VEHICLE', 'Vehicle'), ('OTHER', 'Other')], max_length=20),
        ),
        migrations.AlterField(
            model_name='asset',
            name='assembly',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='churches.church'),
        ),
        migrations.AlterField(
            model_name='asset',
            name='condition',
            field=models.CharField(choices=[('NEW', 'New'), ('GOOD', 'Good'), ('FAIR', 'Fair'), ('OLD', 'Old'), ('NOT_WORKING', 'Not Working')], max_length=20),
        ),
        migrations.AlterField(
            model_name='asset',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_assets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='asset',
            name='quantity',
            field=models.PositiveIntegerField(),
        ),
    ]
