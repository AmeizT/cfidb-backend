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

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        assembly_id = getattr(self.instance, "assembly_id", None) or getattr(
            getattr(request, "user", None), "church_id", None
        )
        fields["spouse"].queryset = Member.objects.filter(assembly_id=assembly_id) if assembly_id else Member.objects.none()
        # Authentication secrets must never be included in member responses.
        fields.pop("access_pin", None)
        return fields

    def validate_avatar(self, value):
        from apps.people.create_security import validate_create_image
        return validate_create_image(value) if value else value

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
            'assembly',
            'created_by',
            'updated_by',
            'is_trash',
            'trash_date',
            'created_at',
            'updated_at',
            'pin_set',
            'access_pin',
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
        request = self.context.get("request")
        if self.instance is None and request is not None:
            from apps.people.create_security import active_create_assembly, reject_other_assembly
            reject_other_assembly(request, active_create_assembly(request))
        instance = self.instance
        first_name = attrs.get('first_name', getattr(instance, 'first_name', '')).strip()
        last_name = attrs.get('last_name', getattr(instance, 'last_name', '')).strip()
        date_of_birth = attrs.get('date_of_birth', getattr(instance, 'date_of_birth', None))
        phone_number = attrs.get('phone_number', getattr(instance, 'phone_number', '')).strip()
        duplicate = Member.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=date_of_birth,
            phone_number=phone_number,
        )
        if instance is not None:
            duplicate = duplicate.exclude(pk=instance.pk)
        if duplicate.exists():
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
