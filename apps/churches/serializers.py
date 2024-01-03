from rest_framework import serializers
from apps.churches.models import Church
from apps.users.serializers import ListUserSerializer


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'
        
          
class ChurchTrackerSerializer(serializers.ModelSerializer):
    pastor = ListUserSerializer()
    
    class Meta:
        model = Church
        fields = (
            'id',
            'church_id', 
            'pastor',
            'name', 
            'description',
            'address',
            'city',
            'province',
            'country',
            'code',
            'lang',
            'currency',
            'phone',
            'email',
            'avatar',
            'banner',
            'brand',
            'status',
            'created_at',
            'updated_at',
        ) 


        
            

        
        

        
        
