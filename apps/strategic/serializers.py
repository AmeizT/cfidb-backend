from rest_framework import serializers
from apps.strategic.models import StrategyLegacy

class StrategyLegacySerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyLegacy
        fields = '__all__'