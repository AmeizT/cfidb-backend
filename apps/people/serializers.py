from rest_framework import serializers
from apps.people.models import (
    Attendance, 
    Homecell, 
    HCAttendance, 
    Kindred, 
    Member, 
    AttendanceRegister, 
    Tally, 
    Testimony
)
from apps.churches.serializers import ChurchSerializer

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
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
        
        
        
class HomecellSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True)
    church = ChurchSerializer()
    
    class Meta:
        model = Homecell
        fields = ['church', 'group_name', 'leader', 'description', 'members', 'created_at', 'updated_at']
        
        
class CreateHomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = '__all__'   
        
 
class CreateTallySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tally
        fields = '__all__'  
        
        
class TallySerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True)
    class Meta:
        model = Tally
        fields = ['branch', 'editor', 'members', 'service', 'timestamp', 'created_at', 'updated_at'] 