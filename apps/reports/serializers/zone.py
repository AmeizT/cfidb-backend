from rest_framework import serializers


class ZoneAssemblyReportSerializer(serializers.Serializer):
    assembly_id = serializers.IntegerField()
    reports = serializers.ListField()


class ZoneMetricsSerializer(serializers.Serializer):
    zone = serializers.DictField()
    summary = serializers.DictField()

    compliance = serializers.DictField()
    finance = serializers.DictField()
    growth = serializers.DictField()
    ministry = serializers.DictField()

    assemblies = ZoneAssemblyReportSerializer(many=True)