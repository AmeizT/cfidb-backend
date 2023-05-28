from apps.church.models import (
    Church, 
    Demographics, 
    Member
)
from rest_framework import serializers


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        
        
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demographics
        fields = "__all__"
        
     
class DemographicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Demographics  
        fields = "__all__"
        
                
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = "__all__"
        


        
            

        
        

        
        
