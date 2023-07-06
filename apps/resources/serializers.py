from rest_framework import serializers
from apps.resources.models import Resource


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
        