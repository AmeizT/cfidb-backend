from rest_framework import serializers
from apps.churches.models import Church, ImageUpload
from apps.users.serializers import ListUserSerializer, UserNamesSerializer

class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageUpload
        fields = '__all__'


class CreateChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'


class ChurchSerializer(serializers.ModelSerializer):
    pastor = UserNamesSerializer()
    total_members = serializers.SerializerMethodField()

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
            'avatar_fallback',
            'status',
            'total_members',
            'created_at',
            'updated_at',
        )

    def get_total_members(self, obj):
        return obj.total_members 
        
         
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
            'avatar_fallback',
            'status',
            'created_at',
            'updated_at',
        ) 


class AssemblyISOSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "code", "lang", "currency"]


class CountryInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "code", "lang", "currency"]
        
            

        
        

        
        
