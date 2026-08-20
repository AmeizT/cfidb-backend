from datetime import timedelta
from django.utils.timezone import now
from rest_framework import serializers
from apps.churches.models import Church
from apps.users.models import AuthHistory, Profile, Role, User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.churches.models.region import Region, RegionLeadership
from apps.churches.models.zone import Zone
      
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User): # type: ignore
        token = super().get_token(user)
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['username'] = user.username
        token['email'] = user.email
        token['church'] = user.church.id if user.church else None
        token['avatar'] = user.avatar.url if user.avatar else None
        token['avatar_fallback'] = user.avatar_fallback
        token['created_at'] = str(user.created_at)
        token['is_active'] = user.is_active
        token['is_admin'] = user.is_admin

        return token


# class CreateUserSerializer(serializers.ModelSerializer):
#     password = CharField(style={
#         'input_type': 'password'
#     })
#     re_password = CharField(
#         style={'input_type': 'password'}, 
#         label="Confirm Password",
#         write_only=True
#     )
    
#     class Meta:
#         model = User
#         fields = (
#             'first_name',
#             'last_name',
#             'email',
#             'church',
#             'password',
#             're_password',
#         )
#         extra_kwargs = {
#             'password': {'write_only': True},
#             're_password': {'write_only': True}
#         }

#     def create(self, validated_data):
#         user = User.objects.create_user(
#             first_name=validated_data['first_name'],
#             last_name=validated_data['last_name'],
#             email=validated_data['email'],
#         )
#         password = validated_data['password']
#         re_password = validated_data['re_password']

#         if password != re_password:
#             raise serializers.ValidationError('Passwords do not match')
#         elif len(password) < 8 or len(re_password) < 8:
#             raise serializers.ValidationError(
#                 'Password must contain at least 8 characters')

#         user.set_password(password)
#         user.save()
#         return user

class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        style={'input_type': 'password'},
        write_only=True,
    )
    re_password = serializers.CharField(
        style={'input_type': 'password'},
        label="Confirm Password",
        write_only=True
    )

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'roles',
            'church',
            'assemblies',
            'password',
            're_password',
        )
        extra_kwargs = {
            'password': {'write_only': True},
            're_password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data['password']
        re_password = validated_data['re_password']

        if password != re_password:
            raise serializers.ValidationError('Passwords do not match')
        elif len(password) < 8:
            raise serializers.ValidationError(
                'Password must contain at least 8 characters')

        user = User.objects.create_user( # type: ignore
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=password, 
        )

        return user
    

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class RegionLeadershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegionLeadership
        fields = '__all__'


class RegionSerializer(serializers.ModelSerializer):
    class Meta: 
        model: Region
        fields = '__all__'


class AuthHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthHistory
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class AssemblySummarySerializer(serializers.ModelSerializer):
    primary_currency = serializers.SerializerMethodField()

    class Meta:
        model = Church
        fields = ['id', 'public_id', 'name', 'zone', 'country_code', 'locale', 'currency', 'primary_currency', 'avatar', 'avatar_fallback'] 

    def get_primary_currency(self, obj):
        currency = obj.primary_currency
        if currency:
            return currency.currency  # 👈 ONLY the name/code field
        return None

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'
  
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(style={"input_type": "password"}, required=True)
    new_password = serializers.CharField(style={"input_type": "password"}, required=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError({'current_password': 'Does not match'})
        return value  
        
    
class ListUserSerializer(serializers.ModelSerializer):
    assemblies = AssemblySummarySerializer(many=True, read_only=True)
    roles = RoleSerializer(many=True)
    assembly = AssemblySummarySerializer(source='church', read_only=True)
    is_online = serializers.SerializerMethodField()

    def get_is_online(self, obj):
        if obj.last_active:
            return now() - obj.last_active < timedelta(minutes=5)
        return False
    
    class Meta:
        model = User
        fields = (
            'id',
            'user_id', 
            'church',
            'assembly',
            'assemblies',
            'full_name',
            'first_name', 
            'last_name', 
            'username', 
            'email',
            'roles', 
            'avatar', 
            'avatar_fallback',
            'last_active',  
            'is_active',
            'is_online',
            'is_admin',
            'is_onboarded',
            'is_student',
            'is_db_staff',
            'is_academy_staff',
            'is_staff',
            'region_role',
            'created_at', 
            'updated_at',
        ) 
        read_only_fields = ['full_name'] 

class AssignedRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = (
            "id",
            "name",
            "code",
        )


class AssignedZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = (
            "id",
            "name",
            "code",
        )

class CurrentUserSerializer(serializers.ModelSerializer):
    assemblies = AssemblySummarySerializer(many=True, read_only=True)
    roles = RoleSerializer(many=True, read_only=True)
    assembly = AssemblySummarySerializer(source="church", read_only=True)

    region_roles = RegionLeadershipSerializer(many=True, read_only=True)
    is_region_staff = serializers.ReadOnlyField()

    church = serializers.PrimaryKeyRelatedField(
        queryset=Church.objects.all(),
        required=False,
        allow_null=True,
    )

    is_db_staff = serializers.ReadOnlyField()
    is_db_zone_staff = serializers.ReadOnlyField()
    is_academy_staff = serializers.ReadOnlyField()
    is_student = serializers.ReadOnlyField()
    is_staff = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()

    assigned_regions = AssignedRegionSerializer(
        many=True,
        read_only=True,
    )

    assigned_zones = AssignedZoneSerializer(
        many=True,
        read_only=True,
    )

    active_region = serializers.SerializerMethodField()
    can_manage_church_appearance = serializers.SerializerMethodField()

    def get_can_manage_church_appearance(self, obj):
        return bool(
            getattr(obj, "is_overseer", False)
            or getattr(obj, "is_admin", False)
        )

    class Meta:
        model = User
        fields = (
            "id",
            "user_id",
            "full_name",
            "first_name",
            "last_name",
            "username",
            "email",
            "recovery_email",
            "church",
            "assembly",
            "assemblies",
            "roles",
            "is_region_staff",
            "active_region",
            "region_roles",
            "assigned_regions",
            "assigned_zones",
            "avatar",
            "avatar_fallback",
            "is_active",
            "is_admin",
            "can_manage_church_appearance",
            "is_onboarded",
            "is_db_staff",
            "is_db_zone_staff",
            "is_academy_staff",
            "is_student",
            "is_staff",
            "created_at",
            "updated_at",
        )

        read_only_fields = [
            "full_name",
            "assemblies",
            "roles",
            "is_db_staff",
            "is_db_zone_staff",
            "is_academy_staff",
            "is_student",
            "is_staff",
        ]
    
    def validate_church(self, value):
        user = self.context["request"].user
        if value and not user.assemblies.filter(id=value.id).exists():
            raise serializers.ValidationError("You do not belong to this teamspace.")
        return value
    

    def get_active_region(self, obj):
        region = obj.active_region

        if not region:
            return None

        return AssignedRegionSerializer(
            region,
            context=self.context,
        ).data
    

class MinifiedUserSerializer(serializers.ModelSerializer):    
    class Meta:
        model = User
        fields = (
            'id',
            'first_name', 
            'last_name', 
            'username', 
        ) 


class MinimalUserSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "full_name",
            "first_name",
            "last_name",
            "email",
            "roles",
            "avatar",
            "avatar_fallback",
        )

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None

class UserNamesSerializer(serializers.ModelSerializer):    
    class Meta:
        model = User
        fields = (
            'id',
            'first_name', 
            'last_name', 
            'username',
            'avatar',
            'avatar_fallback' 
        ) 


class AuthorSerializer(serializers.ModelSerializer):    
    class Meta:
        model = User
        fields = (
            'id',
            'first_name', 
            'last_name', 
            'roles', 
        )       
        
class UniqueUserCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username', 
            'email', 
        )  
  
