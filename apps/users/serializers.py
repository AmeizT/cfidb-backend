from apps.churches.models import Church
from rest_framework import serializers
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
        token['church'] = user.church.id if user.church else None
        token['avatar'] = user.avatar.url if user.avatar else None
        token['avatar_fallback'] = user.avatar_fallback
        token['created_at'] = str(user.created_at)
        token['is_active'] = user.is_active
        token['is_admin'] = user.is_admin
        token['is_pastor'] = user.is_pastor
        token['is_secretary'] = user.is_secretary
        token['is_overseer'] = user.is_overseer

        return token
    

class CreateUserSerializer(serializers.ModelSerializer):
    password = CharField(style={
        'input_type': 'password'
    })
    re_password = CharField(
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
            'church',
            'password',
            're_password',
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            church=validated_data['church'],
        )
        password = validated_data['password']
        re_password = validated_data['re_password']

        if password != re_password:
            raise serializers.ValidationError('Passwords do not match')
        elif len(password) < 8 or len(re_password) < 8:
            raise serializers.ValidationError(
                'Password must contain at least 8 characters')

        user.set_password(password)
        user.save()
        return user
  
 
class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
        'user', 
        'type',
        'intervals', 
        'sub_total',
        'discount',
        'amount_paid',
        'amount_due',
        'is_premium_active',
        'expires',
        'created',
        'updated', 
    )
 
  
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(style={"input_type": "password"}, required=True)
    new_password = serializers.CharField(style={"input_type": "password"}, required=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError({'current_password': 'Does not match'})
        return value  
        
    
class ListUserSerializer(serializers.ModelSerializer):
    account = AccountSerializer(many=True)
    
    class Meta:
        model = User
        fields = (
            'id',
            'user_id', 
            'church',
            'first_name', 
            'last_name', 
            'username', 
            'email', 
            'avatar', 
            'avatar_fallback',  
            'is_admin',
            'is_pastor',
            'is_secretary',
            'created_at', 
            'updated_at',
            'account',
        )  
        
        
class UniqueUserCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username', 
            'email', 
        )  
  

