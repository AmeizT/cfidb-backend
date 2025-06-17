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
    total_members = serializers.SerializerMethodField()

    class Meta:
        model = Church
        fields = (
            'id',
            'uuid', 
            'assigned_pastors',
            'name', 
            'description',
            'address',
            'city',
            'province',
            'country',
            'country_code',
            'language',
            'currency',
            'phone_number',
            'email',
            'avatar',
            'cover_image',
            'avatar_fallback',
            'status',
            'total_members',
            'created_at',
            'updated_at',
        )

    def get_total_members(self, obj):
        return obj.total_members 
    

class AssemblySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = [
            'name', 
            'avatar',
            'cover_image',
            'avatar_fallback',
            'city',
            'province',
            'country',
        ]
    
       
# class ChurchTrackerSerializer(serializers.ModelSerializer):
#     pastor = ListUserSerializer()
    
#     class Meta:
#         model = Church
#         fields = (
#             'id',
#             'uuid', 
#             'pastor',
#             'name', 
#             'description',
#             'address',
#             'city',
#             'province',
#             'country',
#             'code',
#             'lang',
#             'currency',
#             'phone',
#             'email',
#             'avatar',
#             'banner',
#             'avatar_fallback',
#             'status',
#             'created_at',
#             'updated_at',
#         ) 


class AssemblyISOSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "country_code", "language", "currency"]


class LocaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "country_code", "language", "currency"]


class CountryInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "country_code", "language", "currency"]
        
            

        
        

        
        
