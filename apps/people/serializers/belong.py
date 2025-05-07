from rest_framework import serializers
from apps.people.models import Member

class CheckMemberSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    access_pin = serializers.RegexField(
        regex=r'^\d{4,5}$',
        write_only=True,
        max_length=5,
        min_length=4,
        error_messages={"invalid": "Enter a valid 4 or 5-digit PIN."}
    )
    date_of_birth = serializers.DateField()  # Ensure this field is defined here

class SetPinSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    date_of_birth = serializers.DateField()  # Ensure this field is defined here
    new_pin = serializers.CharField()

class ResetPinSerializer(serializers.Serializer):
    member_id = serializers.IntegerField()
    new_pin = serializers.CharField(min_length=4, max_length=8)


class BelongMemberSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = (
            'id', 
            'member_id', 
            'full_name', 
            'first_name', 
            'last_name', 
            'date_of_birth', 
            'email', 
            'avatar', 
            'avatar_fallback',
            'phone_number', 
            'membership_status', 
            'occupation', 
            'skills', 
            'baptized', 
            'baptized_at',
            'baptized_where', 
            'confirmation_date',
            'created_at', 
            'updated_at'
        )

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url
        return None