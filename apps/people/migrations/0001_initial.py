# Generated by Django 4.2.3 on 2023-10-07 15:27

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('churches', '0007_church_currency'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HCAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leader', models.CharField(blank=True, max_length=255)),
                ('topic', models.CharField(blank=True, max_length=255)),
                ('venue', models.CharField(max_length=255)),
                ('attendance', models.BigIntegerField(default=0)),
                ('adults', models.BigIntegerField(default=0)),
                ('kids', models.BigIntegerField(default=0)),
                ('visitors', models.BigIntegerField(default=0)),
                ('new', models.BigIntegerField(default=0)),
                ('repented', models.BigIntegerField(default=0)),
                ('scriptures', models.TextField(blank=True)),
                ('summary', models.TextField(blank=True)),
                ('achievements', models.TextField(blank=True)),
                ('slug', models.SlugField(blank=True, max_length=255)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hc_church', to='churches.church')),
            ],
            options={
                'verbose_name': 'Homecell Attendance',
                'verbose_name_plural': 'Homecell Attendance',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Testimony',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('homecell', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='testimonies', to='people.hcattendance')),
            ],
            options={
                'verbose_name': 'testimony',
                'verbose_name_plural': 'testimonies',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('avatar_fallback_color', models.CharField(blank=True, max_length=24)),
                ('prefix', models.CharField(blank=True, choices=[('Dr', 'Dr'), ('Eng', 'Eng'), ('Hon', 'Hon'), ('Miss', 'Miss'), ('Mr', 'Mr'), ('Mrs', 'Mrs'), ('Ms', 'Ms'), ('Prof', 'Prof'), ('Rev', 'Rev')], max_length=255)),
                ('first_name', models.CharField(max_length=255)),
                ('middle_name', models.CharField(blank=True, max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('date_of_birth', models.DateField()),
                ('gender', models.CharField(choices=[('Male', 'Male'), ('Female', 'Female')], max_length=255)),
                ('relationship', models.CharField(blank=True, choices=[('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced'), ('Widowed', 'Widowed'), ('Separated', 'Separated'), ('Engaged', 'Engaged'), ('In a Relationship', 'In a Relationship'), ('Domestic Partnership', 'Domestic Partnership'), ('Civil Union', 'Civil Union'), ('Committed', 'Committed'), ('Common-Law Marriage', 'Common-Law Marriage'), ('Traditional Marriage', 'Traditional Marriage'), ('Co-parenting', 'Co-parenting')], max_length=255)),
                ('occupation', models.CharField(blank=True, max_length=255)),
                ('address', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=255)),
                ('country', models.CharField(max_length=255)),
                ('phone', models.CharField(blank=True, max_length=24)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('membersince', models.DateField()),
                ('date_of_baptism', models.DateField(blank=True, null=True)),
                ('tithes', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10)),
                ('ministry', models.CharField(blank=True, choices=[('Administration', 'Administration'), ('Christian education', 'Christian education'), ('Counseling', 'Counseling'), ('Discernment', 'Discernment'), ('Evangelism', 'Evangelism'), ('Giving', 'Giving'), ('Hospitality', 'Hospitality'), ('Intercession', 'Intercession'), ('Leadership', 'Leadership'), ('Media and Communications', 'Media and Communications'), ('Other', 'Other'), ('Praise and Worship', 'Praise and Worship'), ('Ushering', 'Ushering')], max_length=255)),
                ('position', models.CharField(blank=True, choices=[('Sunday School Teacher', 'Sunday School Teacher'), ('Youth Leader', 'Youth Leader'), ('Deacon', 'Deacon'), ('Deaconess', 'Deaconess'), ('Elder', 'Elder'), ('Praise and Worship Director', 'Praise and Worship Director'), ('Pastor', 'Pastor'), ('Senior Pastor', 'Senior Pastor'), ('Overseer', 'Overseer'), ('President', 'President'), ('Media Director', 'Media Director'), ('WOE Leader', 'WOE Leader'), ('Gatekeepers Leader', 'Gatekeepers Leader'), ('House Keeper', 'House Keeper'), ('Home Cell Leader', 'Home Cell Leader'), ('Secretary', 'Secretary'), ('Treasurer', 'Treasurer'), ('Other', 'Other')], max_length=255)),
                ('baptized_at', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='churches.church')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='editor', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Member',
                'verbose_name_plural': 'Members',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Kin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('member_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('avatar_fallback_color', models.CharField(blank=True, max_length=24)),
                ('first_name', models.CharField(max_length=255)),
                ('middle_name', models.CharField(blank=True, max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('date_of_birth', models.DateField()),
                ('gender', models.CharField(choices=[('Male', 'Male'), ('Female', 'Female')], max_length=255)),
                ('relation_with_guardian', models.CharField(blank=True, choices=[('Aunt', 'Aunt'), ('Brother', 'Brother'), ('Child', 'Child'), ('Cousin', 'Cousin'), ('Father', 'Father'), ('Grandparent', 'Grandparent'), ('Mother', 'Mother'), ('Sister', 'Sister'), ('Spouse', 'Spouse'), ('Uncle', 'Uncle')], max_length=255)),
                ('membersince', models.DateField()),
                ('date_of_baptism', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kin', to='churches.church')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kin_creator', to=settings.AUTH_USER_MODEL)),
                ('guardian', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardian', to='people.member')),
            ],
            options={
                'verbose_name': 'kin',
                'verbose_name_plural': 'kins',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Homecell',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('members', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='homecell', to='churches.church')),
            ],
            options={
                'verbose_name': 'homecell',
                'verbose_name_plural': 'homecells',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='hcattendance',
            name='homecell',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='hc_attendance', to='people.homecell'),
        ),
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sunday', models.BigIntegerField(default=0)),
                ('home', models.BigIntegerField(default=0)),
                ('friday', models.BigIntegerField(default=0)),
                ('outreach', models.BigIntegerField(default=0)),
                ('kids', models.BigIntegerField(default=0)),
                ('adults', models.BigIntegerField(default=0)),
                ('visitors', models.BigIntegerField(default=0)),
                ('new', models.BigIntegerField(default=0)),
                ('baptized', models.BigIntegerField(default=0)),
                ('repented', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('church', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance', to='churches.church')),
            ],
            options={
                'verbose_name': 'attendance',
                'verbose_name_plural': 'attendance',
                'ordering': ['-created_at'],
            },
        ),
    ]
