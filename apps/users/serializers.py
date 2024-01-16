from rest_framework import serializers
from apps.churches.models import Church
from rest_framework.fields import CharField
from apps.users.models import User, Account
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
      
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
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
            'role',
            'church',
            'churches',
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

        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            role=validated_data['role'],
            password=password,  # Use the validated password here
        )

        return user

  

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
 
  
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(style={"input_type": "password"}, required=True)
    new_password = serializers.CharField(style={"input_type": "password"}, required=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError({'current_password': 'Does not match'})
        return value  
        
    
class ListUserSerializer(serializers.ModelSerializer):
    churches = ChurchSerializer(many=True)
    
    class Meta:
        model = User
        fields = (
            'id',
            'user_id', 
            'church',
            'churches',
            'first_name', 
            'last_name', 
            'username', 
            'email',
            'role', 
            'avatar', 
            'avatar_fallback',  
            'is_active',
            'is_admin',
            'created_at', 
            'updated_at',
        )  


class MinifiedUserSerializer(serializers.ModelSerializer):    
    class Meta:
        model = User
        fields = (
            'id',
            'first_name', 
            'last_name', 
            'username', 
        ) 
        
        
class UniqueUserCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username', 
            'email', 
        )  
  

