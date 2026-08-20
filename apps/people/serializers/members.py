from rest_framework import serializers
from apps.people.models import (
    Attendance, 
    Homecell, 
    JuniorMember, 
    Member,
    Ministry,
    Position, 
)
from apps.churches.serializers import ChurchSerializer
from apps.users.serializers import AuthorSerializer

class MemberMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'full_name', 'first_name', 'middle_name', 'last_name', 'assembly']
                
class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    spouse_full_name = serializers.SerializerMethodField()
    has_pending_transfer = serializers.SerializerMethodField()
    pending_transfer_id = serializers.SerializerMethodField()
    ministries = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Ministry.objects.all()
    )
    positions = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Position.objects.all()
    )

    class Meta:
        model = Member
        fields = '__all__'
        read_only_fields = [
            'member_key',
            'full_name',
            'age',
            'spouse_full_name',
            'has_pending_transfer',
            'pending_transfer_id',
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def get_age(self, obj):
        return obj.age

    def get_spouse_full_name(self, obj):
        """Return the spouse's full name if they exist."""
        if obj.spouse:
            return obj.spouse.full_name 
        return None

    def get_has_pending_transfer(self, obj):
        return obj.transfer_requests.filter(status="pending_acceptance").exists()

    def get_pending_transfer_id(self, obj):
        pending_transfer = obj.transfer_requests.filter(status="pending_acceptance").first()
        return pending_transfer.id if pending_transfer else None
    
    def validate(self, attrs):
        if Member.objects.filter(
            first_name__iexact=attrs['first_name'].strip(),
            last_name__iexact=attrs['last_name'].strip(),
            date_of_birth=attrs['date_of_birth'],
            phone_number=attrs['phone_number'].strip()
        ).exists():
            raise serializers.ValidationError("A member with the same name, birth date, and phone number already exists.")
        return attrs
    

class CreateJuniorMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuniorMember
        fields = '__all__'
        
        
class JuniorMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True, allow_null=True)

    class Meta:
        model = JuniorMember
        fields = (
            'id',
            'full_name',
            'age',
            'member_key',
            'avatar_fallback',
            'church',
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'gender',
            'guardian',
            'guardian_name',
            'guardian_relationship',
            'membersince',
            'membership_status',
            'baptized_at',
            'created_by',
            'created_at',
            'updated_at',
        )

    def get_full_name(self, obj):
        return " ".join(part for part in (obj.first_name, obj.middle_name, obj.last_name) if part)

    def get_age(self, obj):
        from django.utils import timezone
        today = timezone.localdate()
        return today.year - obj.date_of_birth.year - (
            (today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day)
        )
