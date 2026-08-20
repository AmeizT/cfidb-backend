from rest_framework import serializers

class AssemblyMetricsSerializer(serializers.Serializer):
    assembly = serializers.IntegerField()
    assembly_name = serializers.CharField()
    scores = serializers.DictField()
    risk_level = serializers.CharField()
    trend = serializers.CharField()