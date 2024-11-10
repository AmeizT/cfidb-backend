from rest_framework import serializers
from apps.people.models import (
    Attendance, 
    Homecell, 
    JuniorMember, 
    Member, 
    Tally, 
)
from apps.churches.serializers import ChurchSerializer
from apps.users.serializers import AuthorSerializer
                
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member  
        fields = '__all__'
        
        
class CreateJuniorMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuniorMember
        fields = '__all__'
        
        
class JuniorMemberSerializer(serializers.ModelSerializer):
    guardian = MemberSerializer()

    class Meta:
        model = JuniorMember
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
            'created_by',
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
            'non_church_members',
            'is_archived', 
            'created_at', 
            'updated_at', 
        ]
        

class SimplifiedHomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = [ 
            'church', 
            'group_name', 
            'leader', 
            'description', 
            'members', 
            'non_church_members'
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


class AttendanceSerializer(serializers.ModelSerializer):
    homecell = SimplifiedHomecellSerializer()
    created_by = AuthorSerializer()

    class Meta:
        model = Attendance
        fields = [
            'id',
            'church',
            'created_by',
            'category',
            'preacher',
            'sermon',
            'scriptures',
            'headcount',
            'adults',
            'children',
            'visitors', 
            'newcomers',
            'altar_call', 
            'baptism',
            'summary',
            'achievements',
            'slug',
            'start_time',
            'end_time',
            'timestamp',
            'created_at',
            'updated_at',
            'homecell',
        ]


class CreateAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__' 