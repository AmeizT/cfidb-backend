from rest_framework import serializers
from apps.strategic.models import StrategyLegacy, Strategy

class StrategyLegacySerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyLegacy
        fields = '__all__'


class StrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = Strategy
        fields = '__all__'