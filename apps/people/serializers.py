from rest_framework import serializers
from apps.people.models import (
    Attendance, Homecell, HCAttendance, Members, Testimony
)

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        

class HomeCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ['id', 'church', 'name', 'members', 'description']
        
        
class TestimonySerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimony
        fields = '__all__'


class HCAttendanceSerializer(serializers.ModelSerializer):
    homecell = HomeCellSerializer()
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
        model = Members  
        fields = '__all__'
        
                
