from rest_framework import serializers
from apps.people.models import (
    Attendance, 
    Homecell, 
    JuniorMember, 
    Member,
    Ministry,
    Position, 
    Tally, 
)
from apps.churches.serializers import ChurchSerializer
from apps.users.serializers import AuthorSerializer
                
class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    spouse_full_name = serializers.SerializerMethodField()
    ministries = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Ministry.objects.all()
    )
    positions = serializers.SlugRelatedField(
        many=True, slug_field="name", queryset=Position.objects.all()
    )

    class Meta:
        model = Member
        fields = '__all__'
        read_only_fields = ['member_id', 'full_name', 'age', 'spouse_full_name']

    def get_full_name(self, obj):
        return obj.full_name

    def get_age(self, obj):
        return obj.age

    def get_spouse_full_name(self, obj):
        """Return the spouse's full name if they exist."""
        if obj.spouse:
            return obj.spouse.full_name 
        return None
        
        
class CreateJuniorMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = JuniorMember
        fields = '__all__'
        
        
class JuniorMemberSerializer(serializers.ModelSerializer):
    guardian = MemberSerializer()

    class Meta:
        model = JuniorMember
        fields = (
            'id',
            'member_id',
            'avatar_fallback',
            'church',
            'first_name',
            'middle_name',
            'last_name',
            'date_of_birth',
            'gender',
            'guardian',
            'guardian_relationship',
            'membersince',
            'membership_status',
            'baptized_at',
            'created_by',
            'created_at',
            'updated_at',
        )

                      
class HomecellSerializer(serializers.ModelSerializer):
    leader = MemberSerializer()
    church = ChurchSerializer()
    members = MemberSerializer(many=True)
    
    class Meta:
        model = Homecell
        fields = [
            'id', 
            'church', 
            'group_name', 
            'leader', 
            'description', 
            'members', 
            'non_church_members',
            'is_archived', 
            'created_at', 
            'updated_at', 
        ]
        

class SimplifiedHomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = [ 
            'church', 
            'group_name', 
            'leader', 
            'description', 
            'members', 
            'non_church_members'
        ]


class CreateHomecellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = '__all__'   
        
 
class CreateTallySerializer(serializers.ModelSerializer):
    class Meta:
        model = Tally
        fields = '__all__'  
        
        
class TallySerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True)
    
    class Meta:
        model = Tally
        fields = [
            'branch', 
            'created_by', 
            'members', 
            'category', 
            'timestamp', 
            'created_at', 
            'updated_at'
        ] 


class AttendanceSerializer(serializers.ModelSerializer):
    homecell = SimplifiedHomecellSerializer()
    created_by = AuthorSerializer()

    class Meta:
        model = Attendance
        fields = [
            'id',
            'church',
            'created_by',
            'category',
            'preacher',
            'sermon',
            'scriptures',
            'headcount',
            'adults',
            'children',
            'visitors', 
            'newcomers',
            'altar_call', 
            'baptism',
            'summary',
            'achievements',
            'slug',
            'start_time',
            'end_time',
            'timestamp',
            'created_at',
            'updated_at',
            'homecell',
        ]


class CreateAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__' 