# Generated by Django 4.2.3 on 2023-10-13 13:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('strategy', '0003_rename_content_strategy_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='strategy',
            name='timestamp',
            field=models.DateField(),
        ),
    ]
