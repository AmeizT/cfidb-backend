from rest_framework import serializers
from apps.people.models import Homecell
from apps.people.serializers.members import MemberSerializer


class HomecellSerializer(serializers.ModelSerializer):
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
        validated_data["church"] = request.user.church
        return super().create(validated_data)
    


class HomecellSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Homecell
        fields = ["id", "group_name"]