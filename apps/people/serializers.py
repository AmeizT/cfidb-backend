from rest_framework import serializers
from apps.people.models import (
    Attendance, Homecell, HCAttendance, Kindred, Member, AttendanceRegister, Testimony
)

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        
        


class HomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = '__all__'
        
        
class TestimonySerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimony
        fields = '__all__'


class HCAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HCAttendance
        fields = '__all__'
        
        
# class HCAttendanceSerializer(serializers.ModelSerializer):
#     testimonies = TestimonySerializer(many=True)
#     class Meta:
#         model = HCAttendance
#         fields = [
#             'id',
#             'church',
#             'homecell',
#             'coordinator',
#             'topic',
#             'venue',
#             'attendance',
#             'adults',
#             'kids',
#             'visitors',
#             'new',
#             'repented',
#             'scriptures',
#             'summary',
#             'achievements',
#             'testimonies',
#             'slug',
#             'start_time',
#             'end_time',
#             'created_at',
#             'updated_at',
#         ]
 
     
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member  
        fields = '__all__'
        
        
class CreateKindredSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kindred
        fields = '__all__'
        
        
class KindredSerializer(serializers.ModelSerializer):
    guardian = MemberSerializer()
    class Meta:
        model = Kindred
        fields = (
            'id',
            'member_id',
            'avatar_fallback',
            'church',
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'gender',
            'guardian',
            'guardian_relationship',
            'membersince',
            'baptized_at',
            'editor',
            'created_at',
            'updated_at',
        )

        
                
class AttendanceRegisterSerializer(serializers.ModelSerializer):
    member = MemberSerializer()
    class Meta:
        model = AttendanceRegister
        fields = ['id', 'branch', 'member', 'attendance_date', 'created_at', 'updated_at']