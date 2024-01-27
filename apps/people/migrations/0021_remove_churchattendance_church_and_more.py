# Generated by Django 4.2.9 on 2024-01-25 08:17

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0020_alter_kindred_guardian'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='churchattendance',
            name='church',
        ),
        migrations.RemoveField(
            model_name='testimony',
            name='homecell',
        ),
        migrations.RenameField(
            model_name='attendance',
            old_name='friday',
            new_name='attendance_count',
        ),
        migrations.RenameField(
            model_name='attendance',
            old_name='kids',
            new_name='children',
        ),
        migrations.RenameField(
            model_name='attendance',
            old_name='new_members',
            new_name='newcomers',
        ),
        migrations.RenameField(
            model_name='member',
            old_name='editor',
            new_name='created_by',
        ),
        migrations.RemoveField(
            model_name='attendance',
            name='outreach',
        ),
        migrations.RemoveField(
            model_name='attendance',
            name='sunday',
        ),
        migrations.RemoveField(
            model_name='tally',
            name='service',
        ),
        migrations.AddField(
            model_name='attendance',
            name='achievements',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='category',
            field=models.CharField(blank=True, choices=[('midweek', 'Midweek/Friday Prayer'), ('homecell', 'Homecell'), ('outreach', 'Outreach'), ('other', 'Other'), ('sunday', 'Sunday')], default='sunday', max_length=24),
        ),
        migrations.AddField(
            model_name='attendance',
            name='end_time',
            field=models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0), null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='slug',
            field=models.SlugField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='attendance',
            name='start_time',
            field=models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0), null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='summary',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='member',
            name='membership_status',
            field=models.CharField(blank=True, choices=[('Established', 'Established'), ('Newcomer', 'Newcomer')], default='Established', max_length=255),
        ),
        migrations.AddField(
            model_name='tally',
            name='category',
            field=models.CharField(blank=True, choices=[('midweek', 'Midweek/Friday Prayer'), ('homecell', 'Homecell'), ('outreach', 'Outreach'), ('other', 'Other'), ('sunday', 'Sunday')], default='sunday', max_length=24),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='attendance_date',
            field=models.DateField(blank=True, default=datetime.date(1900, 1, 1), null=True),
        ),
        migrations.AlterField(
            model_name='kindred',
            name='baptized_at',
            field=models.DateField(blank=True, default=datetime.date(1900, 1, 1), null=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='ministry',
            field=models.CharField(blank=True, choices=[('Administration', 'Administration'), ('Christian Education', 'Christian Education'), ('Counseling', 'Counseling'), ('Discernment', 'Discernment'), ('Evangelism', 'Evangelism'), ('Giving', 'Giving'), ('Hospitality', 'Hospitality'), ('Intercession', 'Intercession'), ('Leadership', 'Leadership'), ('Media and Communications', 'Media and Communications'), ('Other', 'Other'), ('Praise and Worship', 'Praise and Worship'), ('Sunday School', 'Sunday School'), ('Ushering', 'Ushering')], max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='position',
            field=models.CharField(blank=True, choices=[('Deacon', 'Deacon'), ('Deaconess', 'Deaconess'), ('Elder', 'Elder'), ('Gatekeepers Leader', 'Gatekeepers Leader'), ('General Overseer', 'General Overseer'), ('House Keeper', 'House Keeper'), ('Home Cell Leader', 'Home Cell Leader'), ('Media Director', 'Media Director'), ('National Overseer', 'National Overseer'), ('Other', 'Other'), ('Pastor', 'Pastor'), ('Praise and Worship Director', 'Praise and Worship Director'), ('President', 'President'), ('Secretary', 'Secretary'), ('Secretary General', 'Secretary General'), ('Senior Pastor', 'Senior Pastor'), ('Sunday School Teacher', 'Sunday School Teacher'), ('Treasurer', 'Treasurer'), ('Usher', 'Usher'), ('WOE Leader', 'WOE Leader'), ('Youth Leader', 'Youth Leader')], max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='prefix',
            field=models.CharField(blank=True, choices=[('Advocate', 'Advocate'), ('Dr', 'Dr'), ('Eng', 'Eng'), ('Hon', 'Hon'), ('Miss', 'Miss'), ('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Ms', 'Ms'), ('Prof', 'Prof'), ('Rev', 'Rev')], max_length=255),
        ),
        migrations.AlterField(
            model_name='tally',
            name='timestamp',
            field=models.DateTimeField(blank=True, default=datetime.datetime(1900, 1, 1, 0, 0), null=True),
        ),
        migrations.DeleteModel(
            name='AttendanceRegister',
        ),
        migrations.DeleteModel(
            name='ChurchAttendance',
        ),
        migrations.DeleteModel(
            name='Testimony',
        ),
    ]
