# Generated by Django 4.2.3 on 2023-09-03 07:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('churches', '0006_church_brand'),
    ]

    operations = [
        migrations.AddField(
            model_name='church',
            name='currency',
            field=models.CharField(blank=True, max_length=12),
        ),
    ]
