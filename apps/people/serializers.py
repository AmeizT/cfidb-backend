from rest_framework import serializers
from apps.people.models import Attendance, Homecell, HCAttendance, Members

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        

class HomeCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ['id', 'church', 'name', 'description']


class HCAttendanceSerializer(serializers.ModelSerializer):
    homecell = HomeCellSerializer()
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
            'activities',
            'achievements',
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
        
                
