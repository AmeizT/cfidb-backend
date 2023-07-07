from rest_framework import serializers
from apps.people.models import Attendance, Members

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'
        
     
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members  
        fields = '__all__'
        
                
