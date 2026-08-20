from rest_framework import serializers


class RegionMetricsSerializer(serializers.Serializer):
    region = serializers.DictField()
    summary = serializers.DictField()

    zones = serializers.ListField(child=serializers.DictField())