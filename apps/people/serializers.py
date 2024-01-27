from rest_framework import serializers
from apps.people.models import (
    Attendance, 
    Homecell, 
    HCAttendance, 
    Kindred, 
    Member, 
    Tally, 
)
from apps.churches.serializers import ChurchSerializer

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
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
            'membership_status',
            'baptized_at',
            'editor',
            'created_at',
            'updated_at',
        )

                      
class HomecellSerializer(serializers.ModelSerializer):
    leader = MemberSerializer()
    church = ChurchSerializer()
    members = MemberSerializer(many=True)
    
    class Meta:
        model = Homecell
        fields = [
            'id', 
            'church', 
            'group_name', 
            'leader', 
            'description', 
            'members', 
            'is_archived', 
            'created_at', 
            'updated_at', 
        ]
        
        
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
        fields = [
            'branch', 
            'created_by', 
            'members', 
            'category', 
            'timestamp', 
            'created_at', 
            'updated_at'
        ] 