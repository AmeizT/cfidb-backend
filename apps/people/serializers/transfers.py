from rest_framework import serializers

from apps.churches.models import Church
from apps.people.models import AssemblyMembership, Member, MemberTransferRequest


class AssemblyMembershipSerializer(serializers.ModelSerializer):
    member_full_name = serializers.CharField(source="member.full_name", read_only=True)
    assembly_name = serializers.CharField(source="assembly.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    status_label = serializers.SerializerMethodField()
    start_date = serializers.DateField(source="joined_on", read_only=True)
    end_date = serializers.DateField(source="ended_on", read_only=True)

    class Meta:
        model = AssemblyMembership
        fields = [
            "id",
            "member",
            "member_full_name",
            "assembly",
            "assembly_name",
            "joined_on",
            "ended_on",
            "start_date",
            "end_date",
            "end_reason",
            "end_notes",
            "transfer",
            "status",
            "status_label",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
            "updated_by",
        ]
        read_only_fields = fields

    def get_status_label(self, obj):
        return obj.get_status_display()


class MemberTransferRequestListSerializer(serializers.ModelSerializer):
    member_full_name = serializers.CharField(source="member.full_name", read_only=True)
    member_key = serializers.CharField(source="member.member_key", read_only=True)
    from_assembly_name = serializers.CharField(source="from_assembly.name", read_only=True)
    to_assembly_name = serializers.CharField(source="to_assembly.name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.full_name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.full_name", read_only=True)
    completed_by_name = serializers.CharField(source="completed_by.full_name", read_only=True)
    status_label = serializers.SerializerMethodField()
    has_pending_transfer = serializers.SerializerMethodField()
    source_membership_id = serializers.SerializerMethodField()
    destination_membership_id = serializers.SerializerMethodField()

    class Meta:
        model = MemberTransferRequest
        fields = [
            "id",
            "member",
            "member_key",
            "member_full_name",
            "from_assembly",
            "from_assembly_name",
            "to_assembly",
            "to_assembly_name",
            "status",
            "status_label",
            "effective_date",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "reviewed_by",
            "reviewed_by_name",
            "completed_by",
            "completed_by_name",
            "reviewed_at",
            "completed_at",
            "has_pending_transfer",
            "source_membership_id",
            "destination_membership_id",
        ]
        read_only_fields = fields

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_has_pending_transfer(self, obj):
        return obj.status == MemberTransferRequest.Status.PENDING

    def _membership_id(self, obj, assembly_id, current):
        queryset = obj.assembly_membership_changes.filter(assembly_id=assembly_id)
        if current:
            queryset = queryset.filter(status__in=["active", "inactive"])
        else:
            queryset = queryset.filter(status="ended")
        return queryset.values_list("id", flat=True).first()

    def get_source_membership_id(self, obj):
        return self._membership_id(obj, obj.from_assembly_id, False)

    def get_destination_membership_id(self, obj):
        return self._membership_id(obj, obj.to_assembly_id, True)


class MemberTransferRequestDetailSerializer(MemberTransferRequestListSerializer):
    member_summary = serializers.SerializerMethodField()

    class Meta(MemberTransferRequestListSerializer.Meta):
        fields = MemberTransferRequestListSerializer.Meta.fields + [
            "reason",
            "notes",
            "rejection_reason",
            "member_summary",
            "created_at",
            "updated_at",
        ]

    def get_member_summary(self, obj):
        return {
            "id": obj.member_id,
            "member_key": obj.member.member_key,
            "full_name": obj.member.full_name,
            "membership_status": obj.member.membership_status,
            "membership_stage": obj.member.membership_stage,
            "assembly": obj.member.assembly_id,
        }


class MemberTransferRequestCreateSerializer(serializers.Serializer):
    member = serializers.PrimaryKeyRelatedField(queryset=Member.objects.all())
    to_assembly = serializers.PrimaryKeyRelatedField(queryset=Church.objects.all())
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        member = attrs["member"]
        to_assembly = attrs["to_assembly"]

        if member.assembly_id == to_assembly.id:
            raise serializers.ValidationError({
                "to_assembly": "To assembly must be different from the current assembly."
            })

        if MemberTransferRequest.objects.filter(
            member=member,
            status=MemberTransferRequest.Status.PENDING,
        ).exists():
            raise serializers.ValidationError({
                "member": "This member already has a pending transfer request."
            })

        return attrs


class MemberTransferAcceptSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


class MemberTransferRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=True, allow_blank=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class MemberTransferCancelSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)
