from rest_framework import serializers
from apps.people.models import Attendance, Homecell, HCAttendance, Members

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        

class HomeCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ['church', 'title', 'description', 'leader']


class HCAttendanceSerializer(serializers.ModelSerializer):
    homecell = HomeCellSerializer()
    class Meta:
        model = HCAttendance
        fields = [
            'homecell',
            'start_time', 
            'end_time',
            'venue',
            'attendance',
            'visitors',
            'new',
            'repented',
            'activities',
            'achievements',   
            'created_at', 
            'updated_at'
        ]
     
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members  
        fields = '__all__'
        
                
