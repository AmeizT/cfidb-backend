from rest_framework import serializers
from apps.people.models import (
    Attendance, Homecell, HCAttendance, Kin, Member, Testimony
)

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        

class HomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ['id', 'church', 'name', 'members', 'description']
        
        
class TestimonySerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimony
        fields = '__all__'


class HCAttendanceSerializer(serializers.ModelSerializer):
    homecell = HomecellSerializer()
    testimonies = TestimonySerializer(many=True)
    class Meta:
        model = HCAttendance
        fields = [
            'id',
            'church',
            'homecell',
            'leader',
            'topic',
            'venue',
            'attendance',
            'adults',
            'kids',
            'visitors',
            'new',
            'repented',
            'scriptures',
            'testimonies',
            'summary',
            'achievements',
            'testimonies',
            'slug',
            'start_time',
            'end_time',
            'created_at',
            'updated_at',
        ]
     
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member  
        fields = '__all__'
        
        
class KinSerializer(serializers.ModelSerializer):
    guardian = MemberSerializer()
    class Meta:
        model = Kin
        fields = (
            'id',
            'member_id',
            'avatar_fallback_color',
            'church',
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'gender',
            'guardian',
            'relation_with_guardian',
            'membersince',
            'date_of_baptism',
            'created_by',
            'created_at',
            'updated_at',
        )

        
                
