from pyclbr import Class

from rest_framework import serializers
from apps.churches.models import AssemblyCurrency, Church, Zone, ZoneLeadership
from apps.users.serializers import UserNamesSerializer
from apps.churches.appearance import CHURCH_APPEARANCE_COLORS


class ChurchAppearanceSerializer(serializers.Serializer):
    avatar_fallback = serializers.ChoiceField(choices=sorted(CHURCH_APPEARANCE_COLORS))

class CreateChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'


class ZoneLeadershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneLeadership
        fields = '__all__'  


class ZoneSerializer(serializers.ModelSerializer):
    leadership = ZoneLeadershipSerializer(many=True, read_only=True)

    class Meta:
        model = Zone
        fields = [
            'name', 
            'code',
            'description', 
            'office_location',
            'office_address',
            'office_phone',
            'office_email', 
            'is_active',
            'created_at',
            'updated_at',
            'leadership',
        ]

class AssemblyCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssemblyCurrency
        fields = '__all__'


class ChurchSerializer(serializers.ModelSerializer):
    zone = ZoneSerializer(read_only=True)
    currencies = AssemblyCurrencySerializer(many=True, read_only=True) 
    assigned_pastors = UserNamesSerializer(many=True, read_only=True)
    primary_currency = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    years_active = serializers.SerializerMethodField()
    

    class Meta:
        model = Church
        fields = "__all__"
        extra_kwargs = {
            "public_id": {"read_only": True},
            "avatar_fallback": {"required": False},
        }

    def get_total_members(self, obj):
        return obj.total_members
    
    def get_years_active(self, obj):
        return obj.years_active
    
    def get_primary_currency(self, obj):
        currency = obj.primary_currency
        if currency:
            return currency.currency  # 👈 ONLY the name/code field
        return None
    

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
        fields = ['id', 'country_code', 'language', 'currency']


class LocaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ['id', 'country_code', 'language', 'currency']


class CountryInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ['id', 'country_code', 'language', 'currency']
        
            

        
        

        
        
