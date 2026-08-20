from django.db import transaction
from apps.bookkeeper.models import Tithe
from apps.people.serializers import MemberMinifiedSerializer
from rest_framework import serializers


class TitheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tithe
        fields = "__all__"
        read_only_fields = ["assembly", "report"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["member"] = (
            MemberMinifiedSerializer(instance.member).data
            if instance.member_id
            else None
        )
        return data


class BulkTitheSerializer(serializers.ListSerializer):

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        created = []
        for item in validated_data:
            item["assembly"] = user.church
            instance = Tithe(**item)
            instance._current_user = user
            instance.full_clean()
            instance.save()
            created.append(instance)
        return created


class TitheWriteSerializer(TitheSerializer):
    class Meta(TitheSerializer.Meta):
        list_serializer_class = BulkTitheSerializer


        
