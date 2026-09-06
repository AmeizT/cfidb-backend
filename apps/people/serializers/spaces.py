from rest_framework import serializers
from apps.people.models import Homecell
from apps.people.serializers.members import MemberSerializer


class HomecellSerializer(serializers.ModelSerializer):
    assembly = serializers.IntegerField(source="church_id", read_only=True)
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        assembly_id = getattr(self.instance, "church_id", None) or getattr(
            getattr(request, "user", None), "church_id", None
        )
        from apps.people.models import Member
        members = Member.objects.filter(assembly_id=assembly_id) if assembly_id else Member.objects.none()
        fields["leader_id"].queryset = members
        fields["member_ids"].child_relation.queryset = members
        return fields

    def validate(self, attrs):
        if self.instance is None:
            from apps.people.create_security import active_create_assembly, reject_other_assembly
            request = self.context["request"]
            reject_other_assembly(request, active_create_assembly(request))
        return attrs

    leader = MemberSerializer(read_only=True)
    members = MemberSerializer(many=True, read_only=True)

    leader_id = serializers.PrimaryKeyRelatedField(
        queryset=Homecell._meta.get_field("leader").related_model.objects.all(),
        source="leader",
        write_only=True,
        required=False
    )

    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=Homecell._meta.get_field("members").related_model.objects.all(),
        source="members",
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Homecell
        fields = [
            "id",
            "assembly",
            "group_name",
            "description",
            "leader",
            "leader_id",
            "members",
            "member_ids",
            "non_church_members",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context["request"]
        from apps.people.create_security import active_create_assembly
        validated_data["church"] = active_create_assembly(request)
        return super().create(validated_data)
    


class HomecellSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ["id", "group_name"]
