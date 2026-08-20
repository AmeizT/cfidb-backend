# from django.db import models
# from apps.users.models import User
# from datetime import date
# from django.utils.text import slugify
# from apps.churches.models import Church
# from apps.people.choices import (
#     AttendanceCategories,
#     ServiceType,
#     WeatherCondition
# )

# class Attendance(models.Model):
#     church = models.ForeignKey(
#         Church, 
#         on_delete=models.CASCADE, 
#         related_name="attendance",
#         db_index=True
#     )
#     report = models.ForeignKey(
#         "reports.AssemblyReport",
#         on_delete=models.PROTECT,  
#         null=True,                  
#         blank=True,
#         related_name="%(class)s_set", 
#     )
#     created_by = models.ForeignKey(
#         User, 
#         on_delete=models.SET_NULL, 
#         related_name="attendance_editor", 
#         blank=True, 
#         null=True
#     )
#     homecell = models.ForeignKey(
#         Homecell, 
#         on_delete=models.SET_NULL, 
#         related_name="homecell", 
#         blank=True, 
#         null=True
#     )
#     category = models.CharField(
#         max_length=24, 
#         blank=True, 
#         choices=AttendanceCategories.choices,
#         default=AttendanceCategories.SUNDAY
#     )
#     service_type = models.CharField(
#         max_length=20,
#         choices=ServiceType.choices,
#         default=ServiceType.MAIN,
#         db_index=True
#     )
#     preacher = models.CharField(max_length=255, blank=True)
#     sermon = models.TextField(blank=True)
#     scriptures = models.TextField(blank=True)
#     adults = models.PositiveIntegerField(default=0)
#     children = models.PositiveIntegerField(default=0)
#     guest_attendance = models.PositiveIntegerField(default=0)
#     new_converts = models.PositiveIntegerField(default=0)
#     altar_call = models.PositiveIntegerField(default=0)
#     baptisms = models.PositiveIntegerField(default=0)
#     online_viewers = models.PositiveIntegerField(default=0)
#     volunteers_on_duty = models.PositiveIntegerField(default=0)
#     followups_scheduled = models.PositiveIntegerField(default=0)
#     total_leaders_present = models.PositiveIntegerField(default=0)

#     weather = models.CharField(
#         max_length=30,
#         choices=WeatherCondition.choices,
#         blank=True,
#         null=True,
#         db_index=True
#     )
#     is_special_event = models.BooleanField(default=False)
#     special_event_name = models.CharField(max_length=255, blank=True)
#     notes = models.TextField(blank=True)
#     slug = models.SlugField(max_length=255, blank=True)
#     timestamp = models.DateField(
#         null=True, 
#         blank=True, 
#         db_index=True,
#         default=date(1900, 1, 1),
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = "attendance"
#         verbose_name_plural = "attendance"
#         ordering = ["-timestamp"] 
#         models.UniqueConstraint(
#             fields=["church", "timestamp", "category", "homecell"],
#             name="unique_service_attendance"
#         )

#     def __str__(self):
#         return f"{self.timestamp} - {self.church} - {self.category}"
    
#     @property
#     def headcount(self):
#         return self.adults + self.children + self.guest_attendance
    
#     def save(self, *args, **kwargs):
#         if not self.slug:
#             base_slug = slugify(self.church.name, allow_unicode=True)
#             sermon_slug = slugify(self.sermon, allow_unicode=True)
#             self.slug = f"{sermon_slug}-{base_slug}"
#             counter = 1
#             while Attendance.objects.filter(slug=self.slug).exists():
#                 self.slug = f"{sermon_slug}-{base_slug}-{counter}"
#                 counter += 1

#         super().save(*args, **kwargs)














