from apps.users.models import User
from apps.church.models import Church
from rest_framework import serializers
from rest_framework.fields import CharField
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)

        # token['uid'] = str(user.uid)
        token['name'] = user.name
        token['surname'] = user.surname
        token['username'] = user.username
        token['email'] = user.email
        token['church'] = user.church.id if user.church else None
        token['avatar'] = user.avatar.url if user.avatar else None
        token['default_background_color'] = user.default_background_color
        token['created_at'] = str(user.created_at)
        # token['updated_at'] = user.updated_at
        token['is_active'] = user.is_active
        token['is_admin'] = user.is_admin
        token['is_pastor'] = user.is_pastor
        token['is_secretary'] = user.is_secretary

        return token
    

class UserSerializer(serializers.ModelSerializer):
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
            'pk',
            'name',
            'surname',
            'username',
            'email',
            'church',
            'password',
            're_password',
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            name=validated_data['name'],
            surname=validated_data['surname'],
            username=validated_data['username'],
            email=validated_data['email'],
            church=validated_data['church'],
        )
        password = validated_data.pop('password', None)
        re_password = validated_data.pop('re_password', None)

        if password != re_password:
            raise serializers.ValidationError('Passwords do not match')
        elif len(password) < 8 or len(re_password) < 8:
            raise serializers.ValidationError(
                'Password must contain at least 8 characters')
        else:
            user.set_password(password)
        user.save()
        return user
    
        
class ChurchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = "__all__"
        

class ListUserSerializer(serializers.ModelSerializer):
    # church = ChurchSerializer()
    class Meta:
        model = User
        fields = (
            'id',
            'uid', 
            'name', 
            'surname', 
            'username', 
            'email', 
            'avatar', 
            'default_background_color', 
            'created_at', 
            'updated_at', 
            'church',
            'is_admin',
            'is_pastor',
            'is_secretary'
        )  
  

