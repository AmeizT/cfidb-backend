from apps.church.models import Church
from rest_framework import serializers


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        
        

        


        
            

        
        

        
        
